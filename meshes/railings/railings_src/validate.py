"""Structural checks on the exported .glb.

Catches the failure modes that are invisible until an engine chokes on them --
truncated chunks, out-of-range accessors, denormalised normals, tangents that
are not orthogonal to the normal, undecodable images -- plus the four
invariants this asset actually depends on:

  the UV1 packing        nothing may exceed the LUT's peak, or the highlight
                         floods the face instead of drawing a line
  no coincident depth    nothing may be left sitting exactly on top of
                         something else, or it sparkles as the camera moves
  no holes                you must not be able to see inside the solid from
                         straight above or below
  the seam cover         a module's exposed +X end must fit inside the
                         neighbour's round seam post, which is the only reason
                         a curved run has no notch at every joint
  the lens rims          a lens must keep the faces of its proud lip, or it
                         degenerates into a painted rectangle

The last two are the ones worth reading.

**The seam cover.** There is no curve geometry in this kit. A curved run is
straight modules rotated against each other, and the joint disappears because
the post standing on the seam is round and wider than the rails, so it
encloses both rail ends and the wedge between them. The check measures how far
the rails reach at a module end and compares it against the post's *inradius*
-- the flat-to-flat distance, not the circumradius. Using the circumradius
would pass a post whose facet corners clear the rail while its flats do not,
and every joint on every curve would show a notch.

**No holes.** remove_buried_faces deletes a face only when every probe across
it lands inside the solid, and its probes stop a fifth of the way short of the
boundary. A face whose exposed part is a thin rim -- the top of any stacked
course -- therefore reads as fully buried and is deleted, leaving a hole you
can only see by looking along the axis it faces. That shipped twice before
being noticed by eye. The check now shoots a vertical ray at each point of a
grid and asserts the nearest surface faces the viewer; removing the boundary
probes from reshape.py makes it fail immediately.

Run:  python validate.py
"""
import io
import os
import struct
import sys

import numpy as np
from PIL import Image

import config as cfg
import reshape
from glb import read_glb, accessor


def node_geometry(g, bin_, node):
    """(positions, faces, material id per face) for one node's mesh."""
    P, F, M, off = [], [], [], 0
    for prim in g['meshes'][node['mesh']]['primitives']:
        p = np.asarray(accessor(g, bin_, prim['attributes']['POSITION']), float)
        f = np.asarray(accessor(g, bin_, prim['indices']), np.int64).reshape(-1, 3)
        P.append(p)
        F.append(f + off)
        M.append(np.full(len(f), prim['material']))
        off += len(p)
    return np.vstack(P), np.vstack(F), np.concatenate(M)


def profile(pos, x, tol=1e-3):
    """The (y, z) cross-section of everything sitting on the plane X = x.

    Deduplicated, because vertices are split per face and how many copies of a
    corner survive depends on how many faces meeting there happened to be
    buried -- which differs between the two ends of a module and has nothing to
    do with whether they tile. The *set* of corners is the cross-section; the
    multiplicity is an artefact of the cleanup.
    """
    sel = pos[np.abs(pos[:, 0] - x) < tol][:, 1:]
    return np.unique(np.round(sel, 6), axis=0)


def same_profile(a, b, what):
    """Assert two cross-sections describe the same outline.

    Matched by nearest neighbour in both directions rather than by sorting:
    break_coplanar_ties nudges a face along its own normal by 0.4 mm, so a
    corner on a side wall can sit a hair off its opposite number and any
    exact-match or fixed-rounding test would fail on a model that is perfectly
    fine. 0.6 mm is one nudge plus slack, and still far below anything a
    genuine mismatch would produce.
    """
    assert len(a) and len(b), '%s: an end face has no geometry' % what
    assert len(a) == len(b), \
        '%s: %d corners on one end face, %d on the other' % (what, len(a), len(b))
    d = max(np.abs(b - p).sum(1).min() for p in a)
    d = max(d, max(np.abs(a - p).sum(1).min() for p in b))
    assert d < 6e-4, '%s: end cross-sections differ by %.2f mm' % (what, d * 1000)
    return d



def surface_from(pos, faces, sign, n=44):
    """Look at the solid along +/-Y and report where you can see inside it.

    Shoot a vertical ray at each point of a grid over the footprint and find
    the first face it hits. Coming down from above, that face must point up;
    coming up from below, it must point down. If the nearest surface faces
    *away* from the viewer, you are looking at the back of an interior wall --
    which is exactly what a hole looks like, because the face that should have
    been in front of it was deleted.

    This exists because that deletion has happened twice: once to the beam
    underside, once to the top of every stacked course on the pillar. Both
    were invisible from every angle the preview happened to use, and both were
    only found by someone looking at the model from underneath.
    """
    tri = pos[faces]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    live = ln > 1e-12
    tri, nrm = tri[live], nrm[live] / ln[live, None]
    horizontal = np.abs(nrm[:, 1]) > 1e-6

    lo, hi = pos.min(0), pos.max(0)
    gx = np.linspace(lo[0], hi[0], n + 2)[1:-1]
    gz = np.linspace(lo[2], hi[2], n + 2)[1:-1]

    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    d = ((b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0])
         + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2]))
    ok = np.abs(d) > 1e-14

    bad = 0
    for px in gx:
        for pz in gz:
            u = (((b[:, 2] - c[:, 2]) * (px - c[:, 0])
                  + (c[:, 0] - b[:, 0]) * (pz - c[:, 2])) / np.where(ok, d, 1))
            w = (((c[:, 2] - a[:, 2]) * (px - c[:, 0])
                  + (a[:, 0] - c[:, 0]) * (pz - c[:, 2])) / np.where(ok, d, 1))
            inside = ok & horizontal & (u >= 0) & (w >= 0) & (u + w <= 1)
            if not inside.any():
                continue
            y = u[inside] * a[inside, 1] + w[inside] * b[inside, 1] \
                + (1 - u[inside] - w[inside]) * c[inside, 1]
            first = np.argmax(y * sign)          # nearest to the viewer
            if nrm[inside][first, 1] * sign < 0:
                bad += 1
    return bad


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    path = cfg.OUTPUT_GLB
    raw = open(path, 'rb').read()

    magic, ver, total = struct.unpack('<4sII', raw[:12])
    assert magic == b'glTF' and ver == 2, 'bad glb header'
    assert total == len(raw), 'header length %d != file length %d' % (total, len(raw))

    g, bin_ = read_glb(path)
    assert len(bin_) == g['buffers'][0]['byteLength'], 'BIN chunk length mismatch'
    for i, v in enumerate(g['bufferViews']):
        assert v['byteOffset'] + v['byteLength'] <= len(bin_), 'bufferView %d overruns' % i

    names = [n['name'] for n in g['nodes']]
    assert names == [n for n, _ in cfg.NODES], \
        'node list is %s, expected %s' % (names, [n for n, _ in cfg.NODES])
    assert g['scenes'][0]['nodes'] == list(range(len(names))), \
        'every module must be a root node of the scene'

    # ------------------------------------------------------------ attributes
    tris = 0
    for node in g['nodes']:
        for prim in g['meshes'][node['mesh']]['primitives']:
            at = prim['attributes']
            P = accessor(g, bin_, at['POSITION'])
            N = accessor(g, bin_, at['NORMAL'])
            T = accessor(g, bin_, at['TANGENT'])
            U0 = accessor(g, bin_, at['TEXCOORD_0'])
            U1 = accessor(g, bin_, at['TEXCOORD_1'])
            I = accessor(g, bin_, prim['indices'])
            tag = '%s/%s' % (node['name'], g['materials'][prim['material']]['name'])

            assert len({len(P), len(N), len(T), len(U0), len(U1)}) == 1, \
                '%s: attribute count mismatch' % tag
            assert I.max() < len(P), '%s: index out of range' % tag
            for a in (P, N, T, U0, U1):
                assert np.isfinite(a).all(), '%s: non-finite attribute data' % tag
            assert abs(np.linalg.norm(N, axis=1) - 1).max() < 1e-4, \
                '%s: normals not unit length' % tag

            # a smoothed normal should never swing far from the surface it sits on
            tf = np.asarray(I, np.int64).reshape(-1, 3)
            tn = np.cross(P[tf[:, 1]] - P[tf[:, 0]], P[tf[:, 2]] - P[tf[:, 0]])
            tn /= np.linalg.norm(tn, axis=1, keepdims=True) + 1e-18
            dev = np.degrees(np.arccos(np.clip(np.einsum(
                'ij,ij->i', np.repeat(tn, 3, axis=0), N[tf.reshape(-1)]), -1, 1)))
            assert dev.max() < 75, \
                '%s: a smoothed normal deviates %.0f deg from its face' % (tag, dev.max())
            assert abs(np.linalg.norm(T[:, :3], axis=1) - 1).max() < 1e-3, \
                '%s: tangents not unit length' % tag
            assert np.abs(np.sum(N * T[:, :3], 1)).max() < 1e-3, \
                '%s: tangent not orthogonal to normal' % tag
            assert set(np.unique(T[:, 3])) <= {-1.0, 1.0}, '%s: bad handedness' % tag

            # UV1 packing invariant: 1 on the edge, 0 at the band limit,
            # negative beyond it. Anything above 1 samples past the LUT's peak,
            # where CLAMP_TO_EDGE holds the brightest value instead of falling
            # off, and the highlight floods the face instead of drawing a line.
            assert U1.max() <= 1.0 + 1e-5, \
                '%s: UV1 exceeds the LUT peak by %.4f' % (tag, U1.max() - 1)
            tris += len(I) // 3

    # ------------------------------------------------------------ per module
    geo = {}
    for node in g['nodes']:
        pos, faces, mat = node_geometry(g, bin_, node)
        geo[node['name']] = (pos, faces, mat)
        lo, hi = pos.min(0), pos.max(0)

        # Rail_Span is rails only -- no posts, not even a seam post -- so it
        # legitimately floats. Everything else has something standing on the
        # ground and must actually reach it.
        if node['name'] != 'Rail_Span':
            assert abs(lo[1]) < 5e-4, \
                '%s does not sit on y=0 (min y %.4f)' % (node['name'], lo[1])

        # you must not be able to see inside the solid from straight above or
        # straight below -- see surface_from() for why this is checked at all
        for sign, where in ((1, 'above'), (-1, 'below')):
            holes = surface_from(pos, faces, sign)
            assert holes == 0, \
                '%s: %d sample points look straight into the solid from %s ' \
                '(a face that should be there was deleted)' % (node['name'], holes, where)

        # nothing may be left sitting at identical depth on top of something else
        pairs = len(reshape._coplanar_overlaps(faces, pos, cfg.ZFIGHT['tolerance'])[0])
        assert pairs == 0, \
            '%s: %d coincident coplanar face pairs remain (z-fighting)' % (node['name'], pairs)

        print('  %-12s %4d tris   x [%+.3f, %+.3f]  y [%.3f, %.3f]  z [%+.3f, %+.3f]'
              % (node['name'], len(faces), lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))

    # Every module owns exactly one pitch of *run*, but not of bounding box:
    # the seam post is centred on x = -0.5 and so hangs past it by its own
    # radius, exactly as a Post_Corner dropped on that node would. The rails
    # are what must start at -0.5.
    for name in ('Rail_Middle', 'Rail_Span', 'Rail_End', 'Rail_Lamp'):
        lo = geo[name][0][:, 0].min()
        assert -cfg.HALF - cfg.POST['base_r'] - 5e-4 <= lo <= -cfg.HALF + 5e-4, \
            '%s starts at x = %.4f, not within a seam post of -%.3f' % (name, lo, cfg.HALF)

    # terminals stand above the run, which is what the drawing's silhouette does
    for name in ('Rail_End', 'Post_Corner'):
        h = geo[name][0][:, 1].max()
        assert abs(h - cfg.HEIGHT) < 5e-4, \
            '%s tops out at %.4f, not HEIGHT %.3f' % (name, h, cfg.HEIGHT)
    assert geo['Rail_Middle'][0][:, 1].max() < cfg.HEIGHT - 0.02, \
        'the run is not clearly lower than the terminals; the silhouette reads flat'

    # a terminal owns a grid node: its mass is centred on x = +0.5, so it can
    # be swapped for Rail_Middle + Post_Corner and put mass in the same place
    over = geo['Post_Corner'][0][:, 0].max()
    for name in ('Rail_End', 'Rail_Lamp'):
        hi = geo[name][0][:, 0].max()
        assert hi > cfg.HALF, '%s does not overhang its grid node' % name
        assert hi - cfg.HALF < over + 0.02, \
            '%s overhangs by %.3f, more than a Post_Corner would' % (name, hi - cfg.HALF)

    # ------------------------------------------------------------ the seam
    # The kit has no curve geometry. A curved run is straight modules rotated
    # against each other, and the joint is hidden because the seam post is a
    # cylinder that encloses both rail ends. That enclosure is the invariant --
    # if a rail ever grows wider than the post is round, every curved run in
    # the game develops a visible notch at every joint, and it will look like
    # a lighting bug rather than a geometry one.
    #
    # Checked two ways: from the config numbers, and from the exported
    # vertices, because the second catches a part that reaches the seam
    # without anyone remembering it is there.
    P = cfg.POST
    R = cfg.RAIL
    half_diag = (R['z'] ** 2 + ((R['upper_y'][1] - R['upper_y'][0]) / 2) ** 2) ** 0.5
    # the post is a polygon, not a circle: what covers every angle is the
    # flat-to-flat inradius. Using the circumradius here would pass a post
    # whose facet corners clear the rail while its flats do not.
    inradius = P['shaft_r'] * np.cos(np.pi / P['sides'])
    assert half_diag < inradius, \
        'a rail half-diagonal is %.4f but the seam post covers only %.4f ' \
        'flat-to-flat; angled joints will show a notch' % (half_diag, inradius)

    # Only the +X end is tested. The -X end is where this module's own seam
    # post stands, so there is nothing there for a neighbour to cover -- and
    # the post's base flange is deliberately wider than the cover radius, so
    # testing that end reports the post itself as a failure.
    for name in ('Rail_Middle', 'Rail_Span', 'Rail_End', 'Rail_Lamp'):
        ends = (-cfg.HALF, cfg.HALF) if name == 'Rail_Span' else (cfg.HALF,)
        for end_x in ends:
            cut = profile(geo[name][0], end_x)
            if not len(cut):
                continue
            reach = float(np.abs(cut[:, 1]).max())      # (y, z) -> column 1 is z
            assert reach < inradius, \
                '%s reaches |z| = %.4f at x = %+.2f, outside the seam post ' \
                'cover %.4f -- an angled joint would not be hidden' \
                % (name, reach, end_x, inradius)
    print('  seam: rails reach |z| <= %.4f at a module end, inside the %.4f '
          'post cover (%.1f mm margin at any angle)'
          % (half_diag, inradius, (inradius - half_diag) * 1000))

    # a post must actually sit on the seam, or there is nothing to hide it in
    for name in ('Rail_Middle', 'Rail_End', 'Rail_Lamp'):
        pos = geo[name][0]
        near = pos[np.abs(pos[:, 0] - (-cfg.HALF)) < P['shaft_r'] * 1.2]
        reach = float(np.abs(near[:, 2]).max())
        assert reach > inradius * 0.95, \
            '%s has no seam post at x = -%.2f (widest thing there is %.4f)' \
            % (name, cfg.HALF, reach)
    print('  seam: Rail_Middle, Rail_End and Rail_Lamp each carry a seam post')

    # ...and only one of them, or every join doubles a post
    assert cfg.HALF not in P['x'], \
        'a module owns the post at -0.5 only; one at +0.5 doubles up at every join'
    spacing = np.diff(sorted(P['x']) + [cfg.HALF])
    assert np.allclose(spacing, spacing[0]), \
        'post spacing %s is uneven once the neighbour supplies the +X post' % spacing
    print('  seam: %d posts at an even %.3f m pitch across a join'
          % (len(P['x']), spacing[0]))

    # ------------------------------------------------------------ the lights
    mats = {m['name']: i for i, m in enumerate(g['materials'])}
    assert 'dark_alloy' in mats and mats['dark_alloy'] == 0, 'material 0 must be the body'
    assert ('strip_light' in mats) == cfg.LIGHTS['strips'], \
        'strip_light material presence does not match LIGHTS'
    assert ('lamp_glass' in mats) == cfg.LIGHTS['lamp'], \
        'lamp_glass material presence does not match LIGHTS'

    if not (cfg.LIGHTS['strips'] or cfg.LIGHTS['lamp']):
        assert len(g['materials']) == 1, \
            'with every light off this should be one material, like bridge.glb'

    for name in ('strip_light', 'lamp_glass'):
        if name not in mats:
            continue
        m = g['materials'][mats[name]]
        # a lens is a flat glowing surface. Give it the edge LUT as well and
        # the highlight draws a bright line down the middle of the light bar,
        # which reads as a crack in it.
        assert 'emissiveTexture' not in m, '%s must not carry the edge LUT' % name
        assert max(m['emissiveFactor']) > 0, '%s is switched on but emits nothing' % name

    # A lens is set PROUD of the surface it sits in, and the faces of that lip
    # are what make it read as an inset bar rather than a painted rectangle.
    # They are also the fragile part: remove_buried_faces probes only
    # BURIED['probe'] outside a face, so if the lip is too shallow every sample
    # on a rim lands back inside the host wall and the whole rim is deleted.
    assert cfg.PROUD > cfg.BURIED['probe'] * 0.8, \
        'PROUD (%.4f) is too small for a probe of %.4f; lens rims will be deleted' \
        % (cfg.PROUD, cfg.BURIED['probe'])
    for name, (pos, faces, mat) in geo.items():
        for lens in ('strip_light', 'lamp_glass'):
            if lens not in mats:
                continue
            sel = mat == mats[lens]
            if not sel.any():
                continue
            t = pos[faces[sel]]
            n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-18
            # a surviving lens is a box minus its buried back: one face is the
            # lit front, the rest are rim. Rim is the majority or the lip is gone.
            front = np.bincount(np.argmax(np.abs(n), axis=1), minlength=3).max()
            rim = 1.0 - front / len(n)
            assert rim > 0.35, \
                '%s/%s: only %.0f%% rim faces -- the proud lip was deleted' \
                % (name, lens, rim * 100)

    # ------------------------------------------------------------ the LUT
    body = g['materials'][0]
    assert 'normalTexture' not in body, 'body must stay flat: no normal map'
    assert 'baseColorTexture' not in body['pbrMetallicRoughness'], \
        'body must stay a plain colour'
    assert body['emissiveTexture'].get('texCoord') == 1, 'the edge LUT must sample UV1'
    s = g['samplers'][g['textures'][body['emissiveTexture']['index']]['sampler']]
    assert s['minFilter'] == 9729, 'edge LUT must sample with LINEAR and no mipmaps'
    assert s['wrapS'] == 33071 and s['wrapT'] == 33071, \
        'edge LUT must use CLAMP_TO_EDGE or the falloff wraps around'

    ext = 'KHR_materials_emissive_strength'
    assert ext in g.get('extensionsUsed', []), '%s not declared in extensionsUsed' % ext
    for m in g['materials']:
        assert ext in m.get('extensions', {}), 'emissive strength missing on %s' % m['name']

    for im in g['images']:
        v = g['bufferViews'][im['bufferView']]
        blob = bin_[v['byteOffset']:v['byteOffset'] + v['byteLength']]
        x = Image.open(io.BytesIO(blob))
        x.load()
        assert im['mimeType'] == 'image/png', \
            '%s is lossy; JPEG rings around a hard falloff ramp' % im['name']
        print('  image %-12s %s %s' % (im['name'], x.format, x.size))
    assert len(g['images']) == 1, \
        'expected only the edge LUT, found %d images' % len(g['images'])

    # The edge highlight is not a light. If the LUT clips, the line stops
    # falling off and reads as a strip lamp instead of a machined edge -- and
    # then LIGHTS is no longer the only thing that decides what glows.
    v = g['bufferViews'][g['images'][0]['bufferView']]
    peak = float(np.asarray(Image.open(io.BytesIO(
        bin_[v['byteOffset']:v['byteOffset'] + v['byteLength']])).convert('RGB')).max()) / 255.0
    assert peak < 1.0, 'the edge LUT clips; the highlight would read as a lamp'
    assert body['emissiveFactor'] == cfg.EDGES['emissive'], \
        'the body carries its own emissive tint on top of the LUT'

    srgb = lambda c: round((c ** (1 / 2.2)) * 255)
    bc = body['pbrMetallicRoughness']['baseColorFactor']
    print('  body albedo sRGB #%02X%02X%02X   roughness %.2f   edge LUT peak %.2f'
          % (srgb(bc[0]), srgb(bc[1]), srgb(bc[2]),
             body['pbrMetallicRoughness']['roughnessFactor'], peak))
    print('  lights: strips %s, lamp %s  (%d materials)'
          % ('on' if cfg.LIGHTS['strips'] else 'off',
             'on' if cfg.LIGHTS['lamp'] else 'off', len(g['materials'])))
    print('OK  %d nodes, %d triangles, %.2f MB' % (len(names), tris, len(raw) / 1e6))


if __name__ == '__main__':
    try:
        main()
    except AssertionError as e:
        print('FAILED:', e)
        sys.exit(1)

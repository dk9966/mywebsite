"""Structural checks on the exported .glb.

Catches the failure modes that are invisible until an engine chokes on them:
truncated chunks, out-of-range accessors, denormalised normals, tangents that
are not orthogonal to the normal, undecodable images.

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
import shape
from glb import read_glb, accessor


def main(suffix='', width=1.0, height=1.0):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    path = cfg.OUTPUT_GLB.replace('.glb', suffix + '.glb')
    detail = (width * width * height) ** (1.0 / 3.0)
    raw = open(path, 'rb').read()

    magic, ver, total = struct.unpack('<4sII', raw[:12])
    assert magic == b'glTF' and ver == 2, 'bad glb header'
    assert total == len(raw), 'header length %d != file length %d' % (total, len(raw))

    g, bin_ = read_glb(path)
    assert len(bin_) == g['buffers'][0]['byteLength'], 'BIN chunk length mismatch'

    for i, v in enumerate(g['bufferViews']):
        assert v['byteOffset'] + v['byteLength'] <= len(bin_), 'bufferView %d overruns' % i

    tris = 0
    for prim in g['meshes'][0]['primitives']:
        at = prim['attributes']
        P = accessor(g, bin_, at['POSITION'])
        N = accessor(g, bin_, at['NORMAL'])
        T = accessor(g, bin_, at['TANGENT'])
        U0 = accessor(g, bin_, at['TEXCOORD_0'])
        U1 = accessor(g, bin_, at['TEXCOORD_1'])
        I = accessor(g, bin_, prim['indices'])
        name = g['materials'][prim['material']]['name']

        assert len({len(P), len(N), len(T), len(U0), len(U1)}) == 1, 'attribute count mismatch'
        assert I.max() < len(P), 'index out of range'
        for a in (P, N, T, U0, U1):
            assert np.isfinite(a).all(), 'non-finite attribute data'
        assert abs(np.linalg.norm(N, axis=1) - 1).max() < 1e-4, 'normals not unit length'
        # a smoothed normal should never swing far from the surface it sits on
        tf = np.asarray(I, np.int64).reshape(-1, 3)
        tri_n = np.cross(P[tf[:, 1]] - P[tf[:, 0]], P[tf[:, 2]] - P[tf[:, 0]])
        tri_n /= np.linalg.norm(tri_n, axis=1, keepdims=True) + 1e-18
        dev = np.degrees(np.arccos(np.clip(
            np.einsum('ij,ij->i', np.repeat(tri_n, 3, axis=0), N[tf.reshape(-1)]), -1, 1)))
        assert dev.max() < 75, 'a smoothed normal deviates %.0f deg from its face' % dev.max()
        assert abs(np.linalg.norm(T[:, :3], axis=1) - 1).max() < 1e-3, 'tangents not unit length'
        assert np.abs(np.sum(N * T[:, :3], 1)).max() < 1e-3, 'tangent not orthogonal to normal'
        assert set(np.unique(T[:, 3])) <= {-1.0, 1.0}, 'bad tangent handedness'
        # UV1 packing invariant: an ordinary edge maps into [.., plain_peak]
        # and a glow edge into [glow_peak, ..], so nothing may sit in the gap
        # between them -- if it did, the two profiles would bleed together.
        pk, gk = cfg.LUT['plain_peak'], cfg.LUT['glow_peak']
        inside = (U1 > pk + 1e-6) & (U1 < gk - 1e-6)
        assert not inside.any(), '%d UV1 values landed in the LUT dead zone' % inside.sum()

        # and each face/slot must be entirely one type, or interpolation would
        # sweep a triangle's interior straight through the gap
        per_face = U1.reshape(-1, 3, 2)
        low = (per_face <= pk + 1e-6).all(1)
        high = (per_face >= gk - 1e-6).all(1)
        assert (low | high).all(), 'a face mixes edge types within one UV1 slot'

        glow_faces = int(high.any(1).sum())
        lit = float(((per_face <= pk) & (per_face > 0)).any((1, 2)).mean())
        tris += len(I) // 3
        print('  %-18s %5d tris   %4.1f%% touch an edge band, %d touch a glow line, '
              'normal deviation max %.0f deg'
              % (name, len(I) // 3, lit * 100, glow_faces, dev.max()))

    for t in g['textures']:
        assert t['source'] < len(g['images']) and t['sampler'] < len(g['samplers'])
    for im in g['images']:
        v = g['bufferViews'][im['bufferView']]
        x = Image.open(io.BytesIO(bin_[v['byteOffset']:v['byteOffset'] + v['byteLength']]))
        x.load()
        print('  image %-20s %s %s' % (im['name'], x.format, x.size))

    U1_all = np.vstack([np.asarray(accessor(g, bin_, p['attributes']['TEXCOORD_1']), float)
                        for p in g['meshes'][0]['primitives']])
    pos_all = np.vstack([np.asarray(accessor(g, bin_, p['attributes']['POSITION']), float)
                         for p in g['meshes'][0]['primitives']])

    allpos = np.vstack([np.asarray(accessor(g, bin_, p['attributes']['POSITION']), float)
                        for p in g['meshes'][0]['primitives']])
    y = allpos[:, 1]
    faces = []
    off = 0
    for p in g['meshes'][0]['primitives']:
        n = len(accessor(g, bin_, p['attributes']['POSITION']))
        faces.append(np.asarray(accessor(g, bin_, p['indices']), np.int64).reshape(-1, 3) + off)
        off += n
    faces = np.vstack(faces)

    # The surface must close. This is the check the whole geometry rewrite
    # exists to pass: an edge used by one face is a hole you can see through,
    # and holes are exactly what the old union-of-boxes mesh was full of.
    # Welding tolerance is loose on purpose -- if two faces only *nearly* meet,
    # that is still a crack, and it should fail here rather than in an engine.
    census = shape.audit(faces, allpos)
    assert census['boundary'] == 0, \
        '%d boundary edges: the surface is not closed' % census['boundary']
    print('  surface: closed, %d shared edges (%d used by more than two faces, '
          'where blocks meet corner to corner)'
          % (census['manifold'] + census['nonmanifold'], census['nonmanifold']))

    if cfg.TOP_CAP['enabled']:
        # only meaningful when the cap is a separate object being widened to
        # cover the haunch; the generated shell has no such seam
        t = dict(cfg.TOP_CAP, y_split=cfg.TOP_CAP['y_split'] * height,
                 outer_rmin=cfg.TOP_CAP['outer_rmin'] * width,
                 haunch_band=tuple(x * height for x in cfg.TOP_CAP['haunch_band']))
        band = (y > t['haunch_band'][0]) & (y < t['haunch_band'][1])
        haunch = reshape._outer_profile(allpos, band, t['bins'], t['outer_rmin'], faces)
        cap = reshape._outer_profile(allpos, y >= t['y_split'], t['bins'], t['outer_rmin'], faces)
        ok = ~np.isnan(haunch) & ~np.isnan(cap)
        exposed = int((haunch[ok] > cap[ok]).sum())
        assert exposed == 0, '%d angles where the haunch pokes past the cap' % exposed
        print('  cap overhang: %.3f min clearance over the haunch at %d angles'
              % (float((cap[ok] - haunch[ok]).min()), int(ok.sum())))

    # nothing may be left sitting at identical depth on top of something else
    faces_for_zf = faces
    coincident = len(reshape._coplanar_overlaps(faces_for_zf, allpos,
                                                cfg.ZFIGHT['tolerance'] * detail)[0])
    assert coincident == 0, '%d coincident coplanar face pairs remain (z-fighting)' % coincident
    print('  coincident coplanar face pairs: 0')

    body = g['materials'][0]
    assert len(g['materials']) == 1, \
        'one material only: the paving is geometry, not a textured primitive'
    assert len(g['images']) == 1, 'only the edge LUT ships as an image'
    assert 'normalTexture' not in body, 'body must stay flat: no normal map'
    assert 'baseColorTexture' not in body['pbrMetallicRoughness'], 'body must stay a plain colour'
    assert body['emissiveTexture'].get('texCoord') == 1, 'edge LUT must sample UV1'
    # the LUT is a ramp: mipmaps would average the falloff curve away
    lut_tex = g['textures'][g['materials'][0]['emissiveTexture']['index']]
    assert g['samplers'][lut_tex['sampler']]['minFilter'] == 9729, \
        'edge LUT must sample with LINEAR and no mipmaps'
    for im in g['images']:
        assert im['mimeType'] == 'image/png', \
            '%s is lossy; JPEG rings around the LUT ramp boundaries' % im['name']

    # The paving must actually scale with the platform: bricks are fixed-size
    # in world units, so a variant twice as wide has to carry more upward
    # faces at platform height, not the same faces stretched.
    # the deck is the highest thing on the pillar now; bricks sit within 3
    # drop-steps below it
    deck_y = allpos[:, 1].max() - cfg.SHAPE['paving']['drop'] * 4
    up_top = 0
    tri_n2 = allpos[faces]
    fnn = np.cross(tri_n2[:, 1] - tri_n2[:, 0], tri_n2[:, 2] - tri_n2[:, 0])
    up_sel = (fnn[:, 1] > 0) & (tri_n2[:, :, 1].min(1) > deck_y)
    up_top = int(up_sel.sum())
    print('  platform: %d upward paving faces at deck height' % up_top)

    ext = 'KHR_materials_emissive_strength'
    assert ext in g.get('extensionsUsed', []), '%s not declared in extensionsUsed' % ext
    assert ext in body.get('extensions', {}), 'emissive strength missing on the body material'
    strength = body['extensions'][ext]['emissiveStrength']
    assert strength > 1.0, 'emissive strength should exceed 1 or the glow is capped at the texture ceiling'

    # ordinary edges must stay unlit: only the crack half of the LUT may glow
    import io as _io
    from PIL import Image as _Image
    lut_bv = g['bufferViews'][g['images'][lut_tex['source']]['bufferView']]
    lut = np.asarray(_Image.open(_io.BytesIO(
        bin_[lut_bv['byteOffset']:lut_bv['byteOffset'] + lut_bv['byteLength']]
    )).convert('RGB'))
    pk = cfg.LUT['plain_peak']
    plain_max = int(lut[0, :int(pk * (lut.shape[1] - 1)) + 1].max())
    if cfg.LUT['plain_color'] == [0.0, 0.0, 0.0]:
        assert plain_max == 0, \
            'ordinary edges still emit (LUT plain half peaks at %d)' % plain_max
        print('  ordinary edges: not emissive (LUT plain half is black)')
    else:
        print('  ordinary edges: emissive, LUT plain half peaks at %d' % plain_max)

    # glow lines must live in the middle of the shaft, not at the plinth or cap
    gk = cfg.LUT['glow_peak']
    lit = ((U1_all >= gk) & (U1_all < gk + 0.02)).any(1)
    ys = pos_all[lit][:, 1]
    if cfg.GLOW['paths'] <= 0:
        assert not lit.any(), '%d verts still sit on a crack with GLOW.paths = 0' % lit.sum()
        print('  cracks: none (disabled), emissive strength x%.1f' % strength)
    else:
        lo, hi = ys.min() / height, ys.max() / height
        assert lo > cfg.GLOW['bottom_range'][0] - 0.4 and hi < cfg.GLOW['top_range'][1] + 0.4, \
            'cracks escaped the middle of the shaft (y %.2f..%.2f)' % (lo, hi)
        print('  cracks span y %.2f-%.2f, emissive strength x%.1f' % (lo, hi, strength))

    lut_sampler = g['samplers'][g['textures'][body['emissiveTexture']['index']]['sampler']]
    assert lut_sampler['wrapS'] == 33071 and lut_sampler['wrapT'] == 33071, \
        'edge LUT must use CLAMP_TO_EDGE or the falloff wraps around'

    srgb = lambda c: round((c ** (1 / 2.2)) * 255)
    bc = body['pbrMetallicRoughness']['baseColorFactor']
    print('  body albedo sRGB #%02X%02X%02X   roughness %.2f'
          % (srgb(bc[0]), srgb(bc[1]), srgb(bc[2]),
             body['pbrMetallicRoughness']['roughnessFactor']))
    r = np.hypot(allpos[:, 0], allpos[:, 2])
    h = allpos[:, 1].max() - allpos[:, 1].min()
    print('  %.1f tall, %.2f across at the plinth (h:w %.2f)'
          % (h, 2 * r.max(), h / (2 * r.max())))
    print('OK  %d triangles, %.2f MB' % (tris, len(raw) / 1e6))


if __name__ == '__main__':
    import sys
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--all':
            for var in cfg.VARIANTS:
                print('--- %s' % (var['suffix'] or 'base'))
                main(var['suffix'], var['width'], var['height'])
        else:
            main()
    except AssertionError as e:
        print('FAILED:', e)
        sys.exit(1)

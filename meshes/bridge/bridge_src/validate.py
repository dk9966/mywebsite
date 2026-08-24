"""Structural checks on the exported .glb.

Catches the failure modes that are invisible until an engine chokes on them:
truncated chunks, out-of-range accessors, denormalised normals, tangents that
are not orthogonal to the normal, undecodable images -- plus the two
invariants this asset actually depends on, the UV1 packing and the fact that
no two surfaces are left sitting at identical depth.

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

        # UV1 packing invariant: 1 on the edge, 0 at the band limit, negative
        # beyond it. Anything above 1 would sample past the LUT's peak, where
        # CLAMP_TO_EDGE holds the brightest value instead of falling off, and
        # the highlight would flood the face instead of drawing a line.
        assert U1.max() <= 1.0 + 1e-5, 'UV1 exceeds the LUT peak by %.4f' % (U1.max() - 1)

        per_face = U1.reshape(-1, 3, 2)
        lit = float((per_face > 0).any((1, 2)).mean())
        tris += len(I) // 3
        print('  %-18s %5d tris   %4.1f%% touch an edge band, '
              'normal deviation max %.0f deg'
              % (name, len(I) // 3, lit * 100, dev.max()))

    for t in g['textures']:
        assert t['source'] < len(g['images']) and t['sampler'] < len(g['samplers'])
    for im in g['images']:
        v = g['bufferViews'][im['bufferView']]
        x = Image.open(io.BytesIO(bin_[v['byteOffset']:v['byteOffset'] + v['byteLength']]))
        x.load()
        assert im['mimeType'] == 'image/png', \
            '%s is lossy; JPEG rings around thin joints and bolt rims' % im['name']
        print('  image %-20s %s %s' % (im['name'], x.format, x.size))

    # ------------------------------------------------------------ geometry
    prims = g['meshes'][0]['primitives']
    pos_all, faces, off = [], [], 0
    for p in prims:
        P = np.asarray(accessor(g, bin_, p['attributes']['POSITION']), float)
        pos_all.append(P)
        faces.append(np.asarray(accessor(g, bin_, p['indices']), np.int64).reshape(-1, 3) + off)
        off += len(P)
    pos_all = np.vstack(pos_all)
    faces = np.vstack(faces)

    # The whole point of solving the arch rise: the exported box must be the
    # drawing's box. 0.5 mm on a 4 m model is a rounding artefact, not slack.
    size = pos_all.max(0) - pos_all.min(0)
    want = np.array([cfg.ENVELOPE['length'], cfg.ENVELOPE['height'], cfg.ENVELOPE['width']])
    err = np.abs(size - want)
    assert err.max() < 5e-4, ('bounds %.4f x %.4f x %.4f do not match the drawing'
                              % tuple(size))
    assert abs(pos_all[:, 1].min()) < 5e-4, 'the model does not sit on y=0'
    print('  bounds %.4f L x %.4f W x %.4f H  (max error %.2f mm)'
          % (size[0], size[2], size[1], err.max() * 1000))

    # The walkway must be solid from above. Planks sit on the slab with grooves
    # between them, and a slab-top face wrongly deleted as buried leaves a slit
    # you can see straight through -- but only from overhead, since what is
    # left underneath is the slab's downward-facing side, which culls away.
    # Every other camera angle shows a perfectly solid deck, so nothing but an
    # explicit test catches it.
    #
    # Scope is the slab's own width, not the model's: the planks cantilever
    # 95 mm past the slab on each side and the gaps between those overhanging
    # ends are open by design.
    tri = pos_all[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-18
    T = tri[n[:, 1] > 0.3][:, :, ::2]            # upward faces, projected to XZ
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    e1 = (b[:, 0] - a[:, 0]), (b[:, 1] - a[:, 1])
    e2 = (c[:, 0] - b[:, 0]), (c[:, 1] - b[:, 1])
    e3 = (a[:, 0] - c[:, 0]), (a[:, 1] - c[:, 1])
    inner = cfg.DECK['slab_z'] - 0.01
    xs = np.linspace(cfg.DECK['plank_x'][0] + 0.01, cfg.DECK['plank_x'][1] - 0.01, 260)
    misses = 0
    for x in xs:
        for z in np.linspace(-inner, inner, 9):
            d1 = e1[0] * (z - a[:, 1]) - e1[1] * (x - a[:, 0])
            d2 = e2[0] * (z - b[:, 1]) - e2[1] * (x - b[:, 0])
            d3 = e3[0] * (z - c[:, 1]) - e3[1] * (x - c[:, 0])
            if not (((d1 >= -1e-9) & (d2 >= -1e-9) & (d3 >= -1e-9)).any()
                    or ((d1 <= 1e-9) & (d2 <= 1e-9) & (d3 <= 1e-9)).any()):
                misses += 1
    assert misses == 0, ('%d points over the walkway have no surface beneath '
                         'them -- a plank groove lost its slab floor' % misses)
    print('  walkway watertight from above: %d probes, 0 see-through'
          % (len(xs) * 9))

    # nothing may be left sitting at identical depth on top of something else
    coincident = len(reshape._coplanar_overlaps(faces, pos_all,
                                                cfg.ZFIGHT['tolerance'])[0])
    assert coincident == 0, '%d coincident coplanar face pairs remain (z-fighting)' % coincident
    print('  coincident coplanar face pairs: 0')

    # ------------------------------------------------------------ materials
    body = g['materials'][0]
    assert 'normalTexture' not in body, 'body must stay flat: no normal map'
    assert 'baseColorTexture' not in body['pbrMetallicRoughness'], 'body must stay a plain colour'
    for mi in (0, 1):
        assert g['materials'][mi]['emissiveTexture'].get('texCoord') == 1, \
            'the edge LUT must sample UV1 on %s' % g['materials'][mi]['name']
    # the LUT is a ramp: mipmaps would average the falloff curve away
    lut_tex = g['textures'][body['emissiveTexture']['index']]
    lut_sampler = g['samplers'][lut_tex['sampler']]
    assert lut_sampler['minFilter'] == 9729, 'edge LUT must sample with LINEAR and no mipmaps'
    assert lut_sampler['wrapS'] == 33071 and lut_sampler['wrapT'] == 33071, \
        'edge LUT must use CLAMP_TO_EDGE or the falloff wraps around'

    # the deck tiles along the span but must clamp across the width, or the
    # bolt rows wrap onto the abutment landings that overhang the walkway
    deck_sampler = g['samplers'][g['textures'][
        g['materials'][1]['pbrMetallicRoughness']['baseColorTexture']['index']]['sampler']]
    assert deck_sampler['wrapS'] == 10497 and deck_sampler['wrapT'] == 33071, \
        'deck must repeat along X and clamp across Z'

    ext = 'KHR_materials_emissive_strength'
    assert ext in g.get('extensionsUsed', []), '%s not declared in extensionsUsed' % ext
    for m in g['materials']:
        assert ext in m.get('extensions', {}), 'emissive strength missing on %s' % m['name']
        assert m['extensions'][ext]['emissiveStrength'] > 1.0, \
            '%s: emissive strength should exceed 1 or the highlight is capped' % m['name']

    # The asset carries no light sources. Emissive exists only as the edge
    # highlight, which lives entirely in the LUT -- so there must be exactly
    # two materials, and neither may declare a bright emissiveFactor of its own
    # or the whole model would glow rather than its edges.
    assert len(g['materials']) == 2, \
        'expected 2 materials, found %d -- has a lamp crept back in?' % len(g['materials'])
    for m in g['materials']:
        assert m['emissiveFactor'] == cfg.EDGES['emissive'], \
            '%s carries its own emissive tint' % m['name']
    peak = float(np.asarray(Image.open(io.BytesIO(
        bin_[g['bufferViews'][g['images'][0]['bufferView']]['byteOffset']:
             g['bufferViews'][g['images'][0]['bufferView']]['byteOffset']
             + g['bufferViews'][g['images'][0]['bufferView']]['byteLength']]
    )).convert('RGB')).max()) / 255.0
    assert peak < 1.0, 'the edge LUT clips; the highlight would read as a lamp'
    print('  no light sources: 2 materials, edge LUT peak %.2f' % peak)

    srgb = lambda c: round((c ** (1 / 2.2)) * 255)
    bc = body['pbrMetallicRoughness']['baseColorFactor']
    print('  body albedo sRGB #%02X%02X%02X   roughness %.2f'
          % (srgb(bc[0]), srgb(bc[1]), srgb(bc[2]),
             body['pbrMetallicRoughness']['roughnessFactor']))
    print('OK  %d triangles, %.2f MB' % (tris, len(raw) / 1e6))


if __name__ == '__main__':
    try:
        main()
    except AssertionError as e:
        print('FAILED:', e)
        sys.exit(1)

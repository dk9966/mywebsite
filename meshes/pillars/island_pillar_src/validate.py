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
        assert abs(np.linalg.norm(T[:, :3], axis=1) - 1).max() < 1e-3, 'tangents not unit length'
        assert np.abs(np.sum(N * T[:, :3], 1)).max() < 1e-3, 'tangent not orthogonal to normal'
        assert set(np.unique(T[:, 3])) <= {-1.0, 1.0}, 'bad tangent handedness'
        assert U1.min() >= 0, 'negative edge distance'
        banded = float((U1.min(1) < 1).mean())
        tris += len(I) // 3
        print('  %-18s %5d tris   %4.1f%% of verts inside an edge band'
              % (name, len(I) // 3, banded * 100))

    for t in g['textures']:
        assert t['source'] < len(g['images']) and t['sampler'] < len(g['samplers'])
    for im in g['images']:
        v = g['bufferViews'][im['bufferView']]
        x = Image.open(io.BytesIO(bin_[v['byteOffset']:v['byteOffset'] + v['byteLength']]))
        x.load()
        print('  image %-20s %s %s' % (im['name'], x.format, x.size))

    body = g['materials'][0]
    assert 'normalTexture' not in body, 'body must stay flat: no normal map'
    assert 'baseColorTexture' not in body['pbrMetallicRoughness'], 'body must stay a plain colour'
    assert body['emissiveTexture'].get('texCoord') == 1, 'edge LUT must sample UV1'
    lut_sampler = g['samplers'][g['textures'][body['emissiveTexture']['index']]['sampler']]
    assert lut_sampler['wrapS'] == 33071 and lut_sampler['wrapT'] == 33071, \
        'edge LUT must use CLAMP_TO_EDGE or the falloff wraps around'

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

"""Render preview images straight from the exported .glb.

Everything is read back out of the file -- geometry, UVs, materials, textures --
so what you see is what the asset actually contains, not what the build script
intended.

Run:  python render_preview.py [output.png]
"""
import io
import os
import sys

import numpy as np
from PIL import Image

import config as cfg
from glb import read_glb, accessor
from raster import render

# Two three-quarter views, a near-elevation for the arch, and a plan view.
# The plan view earns its place: the deck's plank gaps are floored by the slab
# rather than open, and a hole there is invisible from every other angle
# because the slab's underside is single-sided and culls away.
VIEWS = [
    dict(cam=(4.2, 2.35, 4.6),   tgt=(0, 0.16, 0), fov=28, W=780, H=470),
    dict(cam=(-4.6, 2.05, -4.0), tgt=(0, 0.16, 0), fov=28, W=780, H=470),
    dict(cam=(0.0, 0.34, 9.5),   tgt=(0, 0.17, 0), fov=19, W=780, H=470),
    dict(cam=(0.001, 7.4, 0.02), tgt=(0, 0.20, 0), fov=25, W=780, H=470),
]


def load(path):
    g, bin_ = read_glb(path)

    def image(i, srgb=True):
        v = g['bufferViews'][g['images'][i]['bufferView']]
        raw = bin_[v['byteOffset']:v['byteOffset'] + v['byteLength']]
        a = np.asarray(Image.open(io.BytesIO(raw)).convert('RGB')) / 255.0
        return a ** 2.2 if srgb else a          # sRGB maps -> linear

    def material(mi):
        m = g['materials'][mi]
        pbr = m.get('pbrMetallicRoughness', {})
        d = {}
        if 'baseColorTexture' in pbr:
            d['base'] = image(g['textures'][pbr['baseColorTexture']['index']]['source'])
        else:
            f = pbr.get('baseColorFactor', [1, 1, 1, 1])
            d['base'] = np.array(f[:3])[None, None, :] * np.ones((2, 2, 3))
        if 'metallicRoughnessTexture' in pbr:
            d['orm'] = image(g['textures'][pbr['metallicRoughnessTexture']['index']]['source'], False)
        else:
            r = pbr.get('roughnessFactor', 1.0)
            d['orm'] = np.stack([np.ones((2, 2)), np.full((2, 2), r), np.zeros((2, 2))], -1)
        if 'normalTexture' in m:
            d['nrm'] = image(g['textures'][m['normalTexture']['index']]['source'], False)
            d['nscale'] = m['normalTexture'].get('scale', 1.0)
        if 'emissiveTexture' in m:
            d['lut'] = image(g['textures'][m['emissiveTexture']['index']]['source'])
            strength = (m.get('extensions', {})
                         .get('KHR_materials_emissive_strength', {})
                         .get('emissiveStrength', 1.0))
            d['emis'] = [c * strength for c in m['emissiveFactor']]
        else:
            d['lut'] = None
        return d

    P, I, U0, U1, TA, NM, M, off = [], [], [], [], [], [], [], 0
    for prim in g['meshes'][0]['primitives']:
        at = prim['attributes']
        pos = accessor(g, bin_, at['POSITION']).astype(np.float64)
        tris = accessor(g, bin_, prim['indices']).astype(int).reshape(-1, 3)
        P.append(pos)
        U0.append(accessor(g, bin_, at['TEXCOORD_0']).astype(np.float64))
        U1.append(accessor(g, bin_, at['TEXCOORD_1']).astype(np.float64))
        TA.append(accessor(g, bin_, at['TANGENT']).astype(np.float64))
        NM.append(accessor(g, bin_, at['NORMAL']).astype(np.float64))
        I.append(tris + off)
        M += [prim['material']] * len(tris)
        off += len(pos)

    return (np.vstack(P), np.vstack(I), np.vstack(U0), np.vstack(U1),
            np.vstack(TA), np.vstack(NM), np.array(M),
            {i: material(i) for i in range(len(g['materials']))})


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    out = sys.argv[1] if len(sys.argv) > 1 else cfg.PREVIEW_PNG
    P, I, U0, U1, TA, NM, M, mats = load(cfg.OUTPUT_GLB)
    frames = [render(P, I, U0, U1, M, mats, tang=TA, vnorm=NM, **v) for v in VIEWS]
    top = np.concatenate(frames[:2], 1)
    bot = np.concatenate(frames[2:], 1)
    Image.fromarray(np.concatenate([top, bot], 0)).save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()

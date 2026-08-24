"""Render the assembled world from instances.json, to check the layout.

Loads each model file once and draws every instance of it, which is exactly
what the three.js side should do. Uses the same software rasteriser as the
pillar previews, so what you see reflects the actual GLB contents.

    python render_world.py [out.png]
"""
import io
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pillars', 'island_pillar_src'))

from glb import read_glb, accessor          # noqa: E402
from raster import render                   # noqa: E402


def load_model(path):
    """-> per-primitive geometry plus a material dict the rasteriser understands."""
    g, bin_ = read_glb(path)

    def image(i, srgb=True):
        v = g['bufferViews'][g['images'][i]['bufferView']]
        raw = bin_[v['byteOffset']:v['byteOffset'] + v['byteLength']]
        a = np.asarray(Image.open(io.BytesIO(raw)).convert('RGB')) / 255.0
        return a ** 2.2 if srgb else a

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
            s = (m.get('extensions', {})
                  .get('KHR_materials_emissive_strength', {})
                  .get('emissiveStrength', 1.0))
            d['emis'] = [c * s for c in m['emissiveFactor']]
        else:
            d['lut'] = None
        return d

    node_of_mesh = {}
    for n in g.get('nodes', []):
        if 'mesh' in n:
            node_of_mesh.setdefault(n['mesh'], n.get('name'))

    prims = []
    for mi, mesh in enumerate(g['meshes']):
        for pr in mesh['primitives']:
            at = pr['attributes']
            prims.append(dict(
                node=node_of_mesh.get(mi, mesh.get('name')),
                pos=np.asarray(accessor(g, bin_, at['POSITION']), float),
                nrm=np.asarray(accessor(g, bin_, at['NORMAL']), float),
                tan=(np.asarray(accessor(g, bin_, at['TANGENT']), float)
                     if 'TANGENT' in at else None),
                uv0=np.asarray(accessor(g, bin_, at['TEXCOORD_0']), float)
                    if 'TEXCOORD_0' in at else None,
                uv1=np.asarray(accessor(g, bin_, at['TEXCOORD_1']), float)
                    if 'TEXCOORD_1' in at else None,
                idx=np.asarray(accessor(g, bin_, pr['indices']), np.int64).reshape(-1, 3),
                mat=material(pr['material']),
            ))
    return prims


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'world_preview.png')
    data = json.load(open(os.path.join(HERE, 'instances.json')))
    models = {k: load_model(os.path.join(HERE, v)) for k, v in data['models'].items()}

    P, I, U0, U1, TA, NM, M, mats, off, mi = [], [], [], [], [], [], [], {}, 0, 0
    for inst in data['instances']:
        yaw = inst.get('rotation_y', 0.0)
        c, s = math.cos(yaw), math.sin(yaw)
        R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        sc = np.array(inst.get('scale', [1, 1, 1]), float)
        t = np.array(inst['position'], float)
        want = inst.get('node')

        for pr in models[inst['model']]:
            if want and pr['node'] != want:
                continue
            # positions: scale in local space, then rotate, then translate
            p = (pr['pos'] * sc) @ R.T + t
            # normals need the inverse transpose of the scale
            n = (pr['nrm'] / sc) @ R.T
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
            key = id(pr['mat'])
            if key not in mats:
                mats[key] = (mi, pr['mat'])
                mi += 1
            P.append(p)
            NM.append(n)
            TA.append(pr['tan'] if pr['tan'] is not None else np.zeros((len(p), 4)))
            U0.append(pr['uv0'] if pr['uv0'] is not None else np.zeros((len(p), 2)))
            U1.append(pr['uv1'] if pr['uv1'] is not None else np.zeros((len(p), 2)))
            I.append(pr['idx'] + off)
            M.append(np.full(len(pr['idx']), mats[key][0]))
            off += len(p)

    P, I = np.vstack(P), np.vstack(I)
    U0, U1, TA, NM = np.vstack(U0), np.vstack(U1), np.vstack(TA), np.vstack(NM)
    M = np.concatenate(M)
    materials = {i: m for i, m in mats.values()}
    print('drawing %d triangles, %d materials' % (len(I), len(materials)))

    centre = np.array([P[:, 0].mean(), 3.5, P[:, 2].mean()])
    span = max(np.ptp(P[:, 0]), np.ptp(P[:, 2]))
    views = [
        dict(cam=centre + np.array([0.75, 0.62, 1.0]) * span * 1.15, fov=32),
        dict(cam=centre + np.array([-0.9, 0.75, -0.7]) * span * 1.15, fov=32),
    ]
    frames = []
    for v in views:
        frames.append(render(P, I, U0, U1, M, materials, tang=TA, vnorm=NM,
                             W=1400, H=800, cam=tuple(v['cam']),
                             tgt=tuple(centre), fov=v['fov'], bg=(0.06, 0.07, 0.09)))
    Image.fromarray(np.concatenate(frames, 0)).save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()

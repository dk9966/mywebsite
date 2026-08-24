"""Build one real bridge mesh per span, at the exact length it needs.

Why this exists
---------------
bridge.glb is a single 4-unit module. Repeating it gave the right total length
but the scene then contained N copies stepping along the gap, not one bridge --
and because each copy was placed level, a span between decks at different
heights came out as a staircase rather than a ramp.

This tiles the module along the span, welds it into one mesh, and shears it to
follow the real line from deck to deck. Output is one GLB per bridge, so each
is a single object of the correct length that you can open and edit on its own.

    python build_bridges.py
"""
import json
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pillars', 'island_pillar_src'))

from glb import read_glb, accessor, GLBWriter     # noqa: E402

MODULE = 4.0            # bridge.glb spans x -2..2
DECK_TOP = 0.30         # walking surface of the deck
RAIL_MODULE = 1.0       # Rail_Span is 1 unit along x
RAIL_INSET = 0.90       # rails sit just inside the deck edge
LAMP_EVERY = 4
OUT_DIR = os.path.join(HERE, '..', 'bridge', 'spans')


def read_module(path, by_node=False):
    """Geometry + the material/texture JSON we need to carry across."""
    g, bin_ = read_glb(path)
    node_of_mesh = {}
    for n in g.get('nodes', []):
        if 'mesh' in n:
            node_of_mesh.setdefault(n['mesh'], n.get('name'))
    prims = []
    for mesh_i, mesh in enumerate(g['meshes']):
        for pr in mesh['primitives']:
            at = pr['attributes']
            prims.append(dict(
                node=node_of_mesh.get(mesh_i, mesh.get('name')),
                material=pr['material'],
                pos=np.asarray(accessor(g, bin_, at['POSITION']), np.float64),
                nrm=np.asarray(accessor(g, bin_, at['NORMAL']), np.float64),
                tan=np.asarray(accessor(g, bin_, at['TANGENT']), np.float64),
                uv0=np.asarray(accessor(g, bin_, at['TEXCOORD_0']), np.float64),
                uv1=np.asarray(accessor(g, bin_, at['TEXCOORD_1']), np.float64),
                idx=np.asarray(accessor(g, bin_, pr['indices']), np.int64).reshape(-1, 3),
            ))
    images = []
    for im in g.get('images', []):
        v = g['bufferViews'][im['bufferView']]
        images.append((im.get('name', 'img'), im['mimeType'],
                       bytes(bin_[v['byteOffset']:v['byteOffset'] + v['byteLength']])))
    return g, prims, images


def merge_materials(base_g, base_images, add_g, add_images):
    """Append a second file's materials/textures/images, remapped."""
    mat_off = len(base_g['materials'])
    smp_off = len(base_g.get('samplers', []))
    img_off = len(base_images)
    base_g['materials'] = base_g['materials'] + json.loads(json.dumps(add_g['materials']))
    base_g.setdefault('samplers', []).extend(add_g.get('samplers', []))
    tex_off = len(base_g.get('textures', []))
    for t in add_g.get('textures', []):
        t = dict(t)
        t['source'] = t['source'] + img_off
        if 'sampler' in t:
            t['sampler'] = t['sampler'] + smp_off
        base_g.setdefault('textures', []).append(t)
    for m in base_g['materials'][mat_off:]:
        pbr = m.get('pbrMetallicRoughness', {})
        for slot in ('baseColorTexture', 'metallicRoughnessTexture'):
            if slot in pbr:
                pbr[slot]['index'] += tex_off
        for slot in ('normalTexture', 'occlusionTexture', 'emissiveTexture'):
            if slot in m:
                m[slot]['index'] += tex_off
    base_images.extend(add_images)
    return mat_off


def rail_pieces(rail_prims, length, rise):
    """Railing runs down both edges of a span, tiled and sheared to match."""
    rails = max(1, int(round(length / RAIL_MODULE)))
    rstep = length / rails
    out = []
    for side in (1, -1):
        for i in range(rails):
            want = ('Rail_Lamp' if i % LAMP_EVERY == LAMP_EVERY // 2
                    else 'Rail_End' if i in (0, rails - 1) else 'Rail_Span')
            x0 = i * rstep
            for pr in rail_prims:
                if pr['node'] != want:
                    continue
                p = pr['pos'].copy()
                p[:, 0] = p[:, 0] * (rstep / RAIL_MODULE) + x0 + rstep / 2.0
                p[:, 2] = p[:, 2] + side * RAIL_INSET
                p[:, 1] = p[:, 1] + DECK_TOP + rise * (p[:, 0] / length)
                out.append((pr, p))
    return out


def build_span(g, prims, images, length, rise, out_path, rail_prims=None,
               rail_mat_off=0):
    """Tile to `length`, shear by `rise`, write a single-mesh GLB.

    The shear is what makes it a ramp: every vertex is lifted in proportion to
    how far along the span it sits, so the deck stays continuous and the ends
    meet both platforms exactly.
    """
    n = max(1, int(round(length / MODULE)))
    step = length / n                      # module length, nudged to divide evenly
    sx = step / MODULE

    w = GLBWriter()
    prim_json = []
    slope = rise / length

    # railings, grouped by source primitive so each keeps its own material
    rails = rail_pieces(rail_prims, length, rise) if rail_prims else []
    grouped = {}
    for pr, p in rails:
        grouped.setdefault(id(pr), (pr, []))[1].append(p)

    for pr in prims:
        P, N, T, U0, U1, I = [], [], [], [], [], []
        off = 0
        for i in range(n):
            x0 = i * step                  # module i occupies [x0, x0+step]
            p = pr['pos'].copy()
            p[:, 0] = p[:, 0] * sx + x0 + step / 2.0
            # shear: lift by how far along the span this vertex is
            p[:, 1] += rise * (p[:, 0] / length)
            P.append(p)
            # the shear tilts the surface, so normals and tangents tilt with it
            slope = rise / length
            nrm = pr['nrm'].copy()
            nrm[:, 1] -= slope * nrm[:, 0] * 0.0      # (shear leaves y-normals)
            nn = nrm.copy()
            nn[:, 0] -= slope * nrm[:, 1]
            nn /= np.linalg.norm(nn, axis=1, keepdims=True) + 1e-12
            N.append(nn)
            tan = pr['tan'].copy()
            tan[:, 1] += slope * tan[:, 0]
            tl = np.linalg.norm(tan[:, :3], axis=1, keepdims=True) + 1e-12
            tan[:, :3] /= tl
            T.append(tan)
            U0.append(pr['uv0'])
            U1.append(pr['uv1'])
            I.append(pr['idx'] + off)
            off += len(p)

        P = np.vstack(P).astype('<f4')
        prim_json.append({
            'attributes': {
                'POSITION': w.add_f32(P, 'VEC3'),
                'NORMAL': w.add_f32(np.vstack(N), 'VEC3'),
                'TANGENT': w.add_f32(np.vstack(T), 'VEC4'),
                'TEXCOORD_0': w.add_f32(np.vstack(U0), 'VEC2'),
                'TEXCOORD_1': w.add_f32(np.vstack(U1), 'VEC2'),
            },
            'indices': w.add_indices(np.vstack(I).reshape(-1).astype(np.uint32)),
            'mode': 4,
            'material': pr['material'],
        })

    for pr, plist in grouped.values():
        P, N, T, U0, U1, I = [], [], [], [], [], []
        off = 0
        for p in plist:
            P.append(p)
            nn = pr['nrm'].copy()
            nn[:, 0] -= slope * nn[:, 1]
            nn /= np.linalg.norm(nn, axis=1, keepdims=True) + 1e-12
            N.append(nn)
            tan = pr['tan'].copy()
            tan[:, 1] += slope * tan[:, 0]
            tan[:, :3] /= np.linalg.norm(tan[:, :3], axis=1, keepdims=True) + 1e-12
            T.append(tan)
            U0.append(pr['uv0'])
            U1.append(pr['uv1'])
            I.append(pr['idx'] + off)
            off += len(p)
        prim_json.append({
            'attributes': {
                'POSITION': w.add_f32(np.vstack(P).astype('<f4'), 'VEC3'),
                'NORMAL': w.add_f32(np.vstack(N), 'VEC3'),
                'TANGENT': w.add_f32(np.vstack(T), 'VEC4'),
                'TEXCOORD_0': w.add_f32(np.vstack(U0), 'VEC2'),
                'TEXCOORD_1': w.add_f32(np.vstack(U1), 'VEC2'),
            },
            'indices': w.add_indices(np.vstack(I).reshape(-1).astype(np.uint32)),
            'mode': 4,
            'material': pr['material'] + rail_mat_off,
        })

    gltf = {
        'asset': {'version': '2.0', 'generator': 'build_bridges.py'},
        'scene': 0, 'scenes': [{'nodes': [0]}],
        'nodes': [{'name': 'bridge', 'mesh': 0}],
        'meshes': [{'name': 'bridge', 'primitives': prim_json}],
        'materials': g['materials'],
        'samplers': g.get('samplers', []),
        'textures': g.get('textures', []),
        'images': [{'bufferView': w.add_image_bytes(data), 'mimeType': mime, 'name': name}
                   for name, mime, data in images],
    }
    if 'extensionsUsed' in g:
        gltf['extensionsUsed'] = g['extensionsUsed']
    for k in ('samplers', 'textures', 'images'):
        if not gltf[k]:
            del gltf[k]
    total = w.write(out_path, gltf)
    return n, total


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    import assemble
    layout = assemble.load_layout()
    metrics = assemble.pillar_metrics(layout)
    ps = layout.get('pillar_scale', 1.0)
    tops = {k: v['height'] * ps for k, v in metrics.items()}
    radii = {k: v['top_radius'] * ps for k, v in metrics.items()}

    g, prims, images = read_module(os.path.join(HERE, layout['models']['bridge']))
    rg, rail_prims, rail_images = read_module(os.path.join(HERE, layout['models']['railings']))
    rail_mat_off = merge_materials(g, images, rg, rail_images)
    spans = {}
    for br in layout['bridges']:
        a, b = layout['islands'][br['a']], layout['islands'][br['b']]
        ha = assemble.deck_height(a, tops)
        hb = assemble.deck_height(b, tops)
        ra, rb = radii[a['pillar']], radii[b['pillar']]
        flat = np.array([b['pos'][0] - a['pos'][0], 0.0, b['pos'][2] - a['pos'][2]])
        dist = np.linalg.norm(flat)
        dirn = flat / dist
        start = np.array(a['pos']) + dirn * ra
        end = np.array(b['pos']) - dirn * rb
        length = float(np.linalg.norm(end[[0, 2]] - start[[0, 2]]))
        rise = float(hb - ha)

        name = 'bridge_%s_%s' % (br['a'], br['b'])
        n, size = build_span(g, prims, images, length, rise,
                             os.path.join(OUT_DIR, name + '.glb'),
                             rail_prims, rail_mat_off)
        spans[name] = dict(length=round(length, 3), rise=round(rise, 3), modules=n,
                           start=[round(v, 3) for v in [start[0], ha, start[2]]],
                           yaw=round(math.atan2(dirn[0], dirn[2]) - math.pi / 2, 5))
        print('%-28s %6.2f long, rise %+5.2f, %d modules -> %5.0f kB'
              % (name, length, rise, n, size / 1024))

    json.dump(spans, open(os.path.join(HERE, 'spans.json'), 'w'), indent=1)
    print('\nwrote %d bridge meshes to %s' % (len(spans), OUT_DIR))


if __name__ == '__main__':
    main()

"""Build the textured island pillar .glb from the untextured mesh.

Run:  python build_pillar.py

Pipeline
--------
1. Read the untextured mesh (positions + indices only, no UVs or normals).
2. Split faces into the top paving disc and the rest of the body.
3. UV0  - triplanar projection for the body, planar disc for the paving.
4. UV1  - per-vertex distance to the two nearest sharp convex edges. This is
          what produces the crisp edge highlight; see the note below.
5. Flat normals + tangents, two primitives, two materials, embedded textures.

Why the edge highlight works
----------------------------
Distance from a point to a straight edge is *linear* across a triangle, so it
interpolates exactly through the rasteriser -- no bake, no atlas, no seams, and
the line keeps a constant world-space width no matter how large the face is.
Two edges per triangle are encoded (u and v), and the LUT resolves min(u, v).
That is lossless here: no triangle in this mesh has more than two sharp convex
edges. Anything past the band clamps to zero via CLAMP_TO_EDGE sampling.
"""
import os
from collections import defaultdict

import numpy as np
from PIL import Image

import config as cfg
from glb import GLBWriter, read_mesh
from textures import make_edge_lut, make_paving

BIG = 40.0          # UV1 value meaning "no sharp edge in this slot"


# ---------------------------------------------------------------- geometry
def face_data(idx, pos):
    tri = pos[idx]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return tri, n, tri.mean(1)


def select_top_disc(fn, centroid):
    t = cfg.TOP_DISC
    return ((fn[:, 1] > t['normal_y']) & (centroid[:, 1] > t['min_height'])
            & (np.hypot(centroid[:, 0], centroid[:, 2]) < t['max_radius']))


def sharp_convex_edges(idx, pos, fn):
    """-> per face, a list of (corner index, highlight band width)."""
    _, inv = np.unique(np.round(pos, 5), axis=0, return_inverse=True)
    F = inv[idx]                                   # welded topology
    shared = defaultdict(list)
    for f in range(len(F)):
        for k in range(3):
            a, b = F[f, k], F[f, (k + 1) % 3]
            shared[(min(a, b), max(a, b))].append((f, k))

    e = cfg.EDGES
    slots = [[] for _ in range(len(F))]
    for faces in shared.values():
        if len(faces) != 2:                        # boundary / non-manifold
            continue
        (f1, k1), (f2, k2) = faces
        ang = np.degrees(np.arccos(np.clip(fn[f1] @ fn[f2], -1, 1)))
        if ang < e['min_angle']:
            continue
        far = pos[idx[f2, (k2 + 2) % 3]]           # the other face's free vertex
        if (far - pos[idx[f1, k1]]) @ fn[f1] >= 0:  # sits in front -> concave
            continue
        scale = np.clip((ang - e['angle_lo']) / (e['angle_hi'] - e['angle_lo']),
                        e['min_scale'], 1.0)
        for f, k in faces:
            slots[f].append((k, e['band'] * scale))
    return slots


def build_uv1(idx, pos, slots):
    """Per-vertex distance to the two nearest sharp edges, normalised by band width."""
    uv1 = np.full((len(pos), 2), BIG, np.float32)
    overflow = 0
    for f, sl in enumerate(slots):
        if not sl:
            continue
        if len(sl) > 2:
            overflow += 1
        p = pos[idx[f]]
        for s, (k, w) in enumerate(sorted(sl, key=lambda t: -t[1])[:2]):
            a, b = p[k], p[(k + 1) % 3]
            e = b - a
            e /= np.linalg.norm(e) + 1e-12
            d = p - a
            d = d - np.outer(d @ e, e)             # perpendicular, in the face plane
            uv1[idx[f], s] = np.linalg.norm(d, axis=1) / w
    return uv1, overflow


def build_uv0(idx, pos, fn, tri, is_disc):
    """Triplanar for the body, planar disc for the paving."""
    uv = np.zeros((len(pos), 2), np.float32)
    T = cfg.TILE
    axis = np.argmax(np.abs(fn), axis=1)
    for f in np.nonzero(~is_disc)[0]:
        v = idx[f]
        p, n, a = pos[v], fn[f], axis[f]
        if a == 1:                                  # up / down facing
            u = p[:, 0] / T
            w = (p[:, 2] / T) if n[1] < 0 else (-p[:, 2] / T)
        elif a == 0:                                # +/-X facing
            u = (p[:, 2] / T) if n[0] > 0 else (-p[:, 2] / T)
            w = p[:, 1] / T
        else:                                       # +/-Z facing
            u = (-p[:, 0] / T) if n[2] > 0 else (p[:, 0] / T)
            w = p[:, 1] / T
        uv[v, 0], uv[v, 1] = u, w

    disc = tri[is_disc].reshape(-1, 3)
    radius = float(np.hypot(disc[:, 0], disc[:, 2]).max()) * cfg.TOP_DISC['uv_margin']
    for f in np.nonzero(is_disc)[0]:
        v = idx[f]
        p = pos[v]
        uv[v, 0] = 0.5 + p[:, 0] / (2 * radius)
        uv[v, 1] = 0.5 - p[:, 2] / (2 * radius)
    return uv, radius


def build_tangents(idx, pos, tri, fn, uv):
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    t = uv[idx]
    d1, d2 = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
    den = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    den = np.where(np.abs(den) < 1e-12, 1e-12, den)
    T = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / den[:, None]
    T -= fn * np.sum(T * fn, axis=1, keepdims=True)          # Gram-Schmidt
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    B = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / den[:, None]
    w = np.where(np.sum(np.cross(fn, T) * B, axis=1) < 0, -1.0, 1.0)
    out = np.zeros((len(pos), 4))
    flat = idx.reshape(-1)
    out[flat, :3] = np.repeat(T, 3, axis=0)
    out[flat, 3] = np.repeat(w, 3)
    return out


# ---------------------------------------------------------------- textures
def prepare_textures(build_dir):
    os.makedirs(build_dir, exist_ok=True)
    p = lambda *a: os.path.join(build_dir, *a)

    make_edge_lut(p('edge_lut.png'))
    make_paving(p('paving_basecolor.png'), p('paving_normal.png'), p('paving_orm.png'))

    for name in ('paving_basecolor', 'paving_orm'):
        Image.open(p(name + '.png')).convert('RGB').save(
            p(name + '.jpg'), quality=cfg.JPEG_QUALITY, subsampling=0)

    # renormalise after downscaling so the normal map stays unit length
    n = Image.open(p('paving_normal.png')).resize(
        (cfg.PAVING_NORMAL_SIZE,) * 2, Image.LANCZOS)
    a = np.asarray(n).astype(np.float32) / 255 * 2 - 1
    a /= np.linalg.norm(a, axis=-1, keepdims=True) + 1e-9
    Image.fromarray(((a * .5 + .5) * 255).astype(np.uint8)).convert('RGB').save(
        p('paving_normal.jpg'), quality=cfg.JPEG_QUALITY, subsampling=0)

    return [(p('edge_lut.png'), 'image/png'),
            (p('paving_basecolor.jpg'), 'image/jpeg'),
            (p('paving_normal.jpg'), 'image/jpeg'),
            (p('paving_orm.jpg'), 'image/jpeg')]


# ---------------------------------------------------------------- export
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    idx, pos = read_mesh(cfg.SOURCE_MESH)
    tri, fn, centroid = face_data(idx, pos)
    is_disc = select_top_disc(fn, centroid)

    slots = sharp_convex_edges(idx, pos, fn)
    uv1, overflow = build_uv1(idx, pos, slots)
    uv0, disc_radius = build_uv0(idx, pos, fn, tri, is_disc)
    tangents = build_tangents(idx, pos, tri, fn, uv0)

    normals = np.zeros_like(pos)
    normals[idx.reshape(-1)] = np.repeat(fn, 3, axis=0)      # flat shading

    print('faces: %d body / %d paving   disc radius %.4f'
          % ((~is_disc).sum(), is_disc.sum(), disc_radius))
    print('faces needing a 3rd edge slot: %d (must be 0)' % overflow)
    assert overflow == 0

    images = prepare_textures(cfg.BUILD_DIR)

    w = GLBWriter()
    primitives = []
    for select, material in ((~is_disc, 0), (is_disc, 1)):
        v = idx[np.nonzero(select)[0]].reshape(-1)
        primitives.append({
            'attributes': {
                'POSITION':   w.add_f32(pos[v], 'VEC3'),
                'NORMAL':     w.add_f32(normals[v], 'VEC3'),
                'TANGENT':    w.add_f32(tangents[v], 'VEC4'),
                'TEXCOORD_0': w.add_f32(uv0[v], 'VEC2'),
                'TEXCOORD_1': w.add_f32(uv1[v], 'VEC2'),
            },
            'indices': w.add_indices(np.arange(len(v), dtype=np.uint32)),
            'mode': 4,
            'material': material,
        })

    gltf_images = [{'bufferView': w.add_image(f), 'mimeType': m,
                    'name': os.path.basename(f).rsplit('.', 1)[0]} for f, m in images]

    gltf = {
        'asset': {'version': '2.0', 'generator': 'island-pillar/build_pillar.py'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'name': 'island_pillar', 'mesh': 0}],
        'meshes': [{'name': 'island_pillar', 'primitives': primitives}],
        'samplers': [
            {'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497},
            {'magFilter': 9729, 'minFilter': 9987, 'wrapS': 33071, 'wrapT': 33071},
        ],
        'images': gltf_images,
        # LUT and paving both clamp; nothing here tiles
        'textures': [{'sampler': 1, 'source': i} for i in range(len(gltf_images))],
        'materials': [
            {'name': 'dark_slate_edges', 'doubleSided': False,
             'pbrMetallicRoughness': {'baseColorFactor': cfg.BODY['base_color'],
                                      'metallicFactor': cfg.BODY['metallic'],
                                      'roughnessFactor': cfg.BODY['roughness']},
             'emissiveTexture': {'index': 0, 'texCoord': 1},
             'emissiveFactor': cfg.EDGES['emissive']},
            {'name': 'circular_brick', 'doubleSided': False,
             'pbrMetallicRoughness': {'baseColorTexture': {'index': 1},
                                      'metallicRoughnessTexture': {'index': 3},
                                      'metallicFactor': 0.0, 'roughnessFactor': 1.0},
             'normalTexture': {'index': 2, 'scale': 0.8}},
        ],
    }

    total = w.write(cfg.OUTPUT_GLB, gltf)
    print('wrote %s  (%.2f MB, %d triangles)'
          % (cfg.OUTPUT_GLB, total / 1e6, len(idx)))


if __name__ == '__main__':
    main()

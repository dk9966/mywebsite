"""Build the bridge .glb from nothing but the numbers in config.py.

Run:  python build_bridge.py

Pipeline
--------
1. Solve the arch rise so the crown lands exactly on the drawing's 60 cm, then
   assemble the model as a union of prisms sheared onto that arch.
2. Delete the faces buried inside the union, and break any coincident-surface
   ties that survive.
3. UV0  - triplanar for the body, planar XZ for the deck plate.
4. UV1  - per-vertex distance to the two nearest sharp convex edges. This is
          what produces the crisp edge highlight; see the note below.
5. Smoothed normals + tangents, two primitives, two materials, embedded maps.

Why the edge highlight works
----------------------------
Distance from a point to a straight edge is *linear* across a triangle, so it
interpolates exactly through the rasteriser -- no bake, no atlas, no seams, and
the line keeps a constant world-space width no matter how large the face is.
Two edges per triangle are encoded (u and v), and the LUT resolves them
together. Anything past the band clamps to zero via CLAMP_TO_EDGE sampling.

The asset has no light sources of any kind -- see the README.
"""
import os
from collections import defaultdict

import numpy as np

import config as cfg
import geometry
import reshape
from glb import GLBWriter
from textures import make_edge_lut, make_plate

DECK_TAGS = {'plank', 'end_plate'}


# ---------------------------------------------------------------- geometry
def face_data(idx, pos):
    tri = pos[idx]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return tri, n, tri.mean(1)


def select_deck(tags, fn):
    """The walking surface: upward faces of the planks and abutment landings.

    Selection is by tag rather than by height or plane, because the deck is an
    arch: there is no single plane to test against, and a height window wide
    enough to catch the crown also catches the abutment landings 140 mm below
    it at the ends of the span.
    """
    return np.isin(tags, list(DECK_TAGS)) & (fn[:, 1] > 0.7)


def sharp_convex_edges(idx, pos, fn, keep=None):
    """Find the mesh's sharp convex edges.

    Returns (welded_positions, edge_list, angles, face_slots) where
    face_slots[f] is a list of (corner, edge_id) for that face.

    Detection runs on the *full* mesh even though buried faces are being
    dropped. Removing a face first would leave its neighbours' shared edges
    with only one adjacent face, so they would stop registering as creases at
    all. Edges are filtered afterwards, keeping only those with at least one
    surviving face.
    """
    welded, inv = np.unique(np.round(pos, 5), axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    F = inv[idx]
    shared = defaultdict(list)
    for f in range(len(F)):
        for k in range(3):
            a, b = F[f, k], F[f, (k + 1) % 3]
            shared[(min(a, b), max(a, b))].append((f, k))

    e = cfg.EDGES
    edges, angles = [], []
    face_slots = [[] for _ in range(len(F))]
    for key, faces in shared.items():
        if len(faces) != 2:                        # boundary / non-manifold
            continue
        (f1, k1), (f2, k2) = faces
        ang = np.degrees(np.arccos(np.clip(fn[f1] @ fn[f2], -1, 1)))
        if ang < e['min_angle']:
            continue
        far = pos[idx[f2, (k2 + 2) % 3]]           # the other face's free vertex
        if (far - pos[idx[f1, k1]]) @ fn[f1] >= 0:  # sits in front -> concave
            continue
        if keep is not None and not (keep[f1] or keep[f2]):
            continue                               # both faces invisible
        eid = len(edges)
        edges.append(key)
        angles.append(ang)
        for f, k in faces:
            face_slots[f].append((k, eid))
    return welded, edges, np.array(angles), face_slots


def build_uv1(idx, pos, welded, edges, angles, face_slots):
    """Pack each vertex's distance to its two nearest sharp edges into UV1.

    Distance to a straight edge is linear across a triangle, so it interpolates
    exactly as a vertex attribute -- that is what makes these lines crisp with
    no bake and no atlas. The value stored is ``1 - d/w``: 1 right on the edge,
    0 at the band limit, and negative past it, where CLAMP_TO_EDGE reads the
    LUT's zero border. Leaving it unclamped is what keeps it linear.

    Two slots per face. Where a triangle has more than two sharp convex edges
    the blunter ones lose, since a wide band is the one least missed.
    """
    e = cfg.EDGES
    scale = np.clip((angles - e['angle_lo']) / (e['angle_hi'] - e['angle_lo']),
                    e['min_scale'], 1.0)

    uv1 = np.zeros((len(pos), 2), np.float32)
    overflow = 0
    for f in range(len(idx)):
        slots = [eid for _, eid in face_slots[f]]
        if not slots:
            continue
        ranked = sorted(slots, key=lambda eid: scale[eid], reverse=True)
        if len(ranked) > 2:
            overflow += 1
        p = pos[idx[f]]
        for s, eid in enumerate(ranked[:2]):
            w = e['band'] * scale[eid]
            a, b = welded[edges[eid][0]], welded[edges[eid][1]]
            d = b - a
            d = d / (np.linalg.norm(d) + 1e-12)
            r = p - a
            r = r - np.outer(r @ d, d)             # perpendicular to the edge line
            t = np.linalg.norm(r, axis=1) / w      # 0 on the edge, 1 at band limit
            uv1[idx[f], s] = 1.0 - t
    return uv1, overflow


def build_uv0(idx, pos, fn, is_deck):
    """Triplanar for the body, planar XZ for the deck.

    The deck's u repeats once per plank pitch and its v spans the walkway, so
    the bolt rows land in the same place on every plank and the painted joint
    lands on the real groove. Getting that alignment for free is the whole
    reason the projection is planar rather than per-face.
    """
    uv = np.zeros((len(pos), 2), np.float32)
    T = cfg.TILE
    axis = np.argmax(np.abs(fn), axis=1)
    for f in np.nonzero(~is_deck)[0]:
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

    D = cfg.DECK
    pitch = (D['plank_x'][1] - D['plank_x'][0]) / D['planks']
    for f in np.nonzero(is_deck)[0]:
        v = idx[f]
        p = pos[v]
        uv[v, 0] = p[:, 0] / pitch + 0.5           # plank centred on the tile
        uv[v, 1] = 0.5 + p[:, 2] / (2 * D['uv_half_width'])
    return uv, pitch


def smooth_normals(idx, pos, fn, threshold_deg, keep=None):
    """Per-vertex normals with smoothing groups.

    Every prism here is sheared onto the arch, so its four side faces are not
    quite planar and the diagonal each quad is cut along ends up with its two
    halves facing very slightly different ways. Flat-shaded, each half catches
    the light differently and the cut line shows up as a visible triangle
    running across what should be a single panel.

    Averaging the normal across any edge whose bend is below ``threshold_deg``
    makes the halves read as one panel, while genuine creases -- every block
    joint on the model -- stay perfectly sharp.

    Only exported faces take part. Buried faces are interior and their
    orientation is arbitrary; averaging a visible normal with one of those
    corrupts the shading of a surface that looks fine.
    """
    if keep is None:
        keep = np.ones(len(idx), bool)
    welded, inv = np.unique(np.round(pos, 5), axis=0, return_inverse=True)
    W = inv.reshape(-1)[idx]

    shared = defaultdict(list)
    for f in np.nonzero(keep)[0]:
        for k in range(3):
            a, b = W[f, k], W[f, (k + 1) % 3]
            shared[(min(a, b), max(a, b))].append(int(f))

    limit = np.cos(np.radians(threshold_deg))
    joins = defaultdict(list)          # welded vertex -> face pairs to merge
    smooth_edges = 0
    for (a, b), faces in shared.items():
        if len(faces) != 2:
            continue
        f1, f2 = faces
        if float(fn[f1] @ fn[f2]) < limit:
            continue                   # a real crease: keep it sharp
        smooth_edges += 1
        joins[a].append((f1, f2))
        joins[b].append((f1, f2))

    corner_of = {}                     # (face, welded vertex) -> corner index
    vert_faces = defaultdict(list)
    for f in np.nonzero(keep)[0]:
        f = int(f)
        for k in range(3):
            corner_of[(f, W[f, k])] = k
            vert_faces[W[f, k]].append(f)

    tri = pos[idx]
    normals = np.repeat(fn, 3, axis=0).reshape(len(idx), 3, 3).copy()
    for v, faces in vert_faces.items():
        pairs = joins.get(v)
        if not pairs:
            continue
        adj = defaultdict(set)
        for f1, f2 in pairs:
            adj[f1].add(f2)
            adj[f2].add(f1)
        seen = set()
        for start in faces:
            if start in seen:
                continue
            group, stack = [], [start]
            seen.add(start)
            while stack:
                f = stack.pop()
                group.append(f)
                for nb in adj.get(f, ()):
                    if nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            if len(group) < 2:
                continue
            acc = np.zeros(3)
            for f in group:
                k = corner_of[(f, v)]
                e1 = tri[f, (k + 1) % 3] - tri[f, k]
                e2 = tri[f, (k + 2) % 3] - tri[f, k]
                n1 = np.linalg.norm(e1)
                n2 = np.linalg.norm(e2)
                if n1 < 1e-12 or n2 < 1e-12:
                    continue
                # weight by the corner angle so a sliver does not dominate
                acc += fn[f] * np.arccos(np.clip(e1 @ e2 / (n1 * n2), -1, 1))
            L = np.linalg.norm(acc)
            if L < 1e-9:
                continue
            acc /= L
            for f in group:
                normals[f, corner_of[(f, v)]] = acc

    print('  normals: %d of %d shared edges smoothed (under %.0f deg)'
          % (smooth_edges, sum(1 for v in shared.values() if len(v) == 2),
             threshold_deg))
    return normals.reshape(-1, 3)


def build_tangents(idx, pos, tri, fn, uv, vertex_normals=None):
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    t = uv[idx]
    d1, d2 = t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]
    den = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    den = np.where(np.abs(den) < 1e-12, 1e-12, den)
    T = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / den[:, None]
    B = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / den[:, None]

    out = np.zeros((len(pos), 4))
    flat = idx.reshape(-1)
    # one tangent per vertex, orthogonalised against that vertex's own normal
    Tv = np.repeat(T, 3, axis=0)
    Bv = np.repeat(B, 3, axis=0)
    Nv = vertex_normals[flat] if vertex_normals is not None else np.repeat(fn, 3, axis=0)
    Tv = Tv - Nv * np.sum(Tv * Nv, axis=1, keepdims=True)    # Gram-Schmidt
    bad = np.linalg.norm(Tv, axis=1) < 1e-8
    if bad.any():                       # degenerate UVs: any orthogonal axis will do
        alt = np.zeros_like(Tv[bad])
        alt[:, 0] = 1.0
        alt = alt - Nv[bad] * np.sum(alt * Nv[bad], axis=1, keepdims=True)
        Tv[bad] = alt
    Tv /= np.linalg.norm(Tv, axis=1, keepdims=True) + 1e-12
    w = np.where(np.sum(np.cross(Nv, Tv) * Bv, axis=1) < 0, -1.0, 1.0)
    out[flat, :3] = Tv
    out[flat, 3] = w
    return out


# ---------------------------------------------------------------- textures
def prepare_textures(build_dir):
    os.makedirs(build_dir, exist_ok=True)
    p = lambda *a: os.path.join(build_dir, *a)

    make_edge_lut(p('edge_lut.png'))
    make_plate(p('deck_basecolor.png'), p('deck_normal.png'), p('deck_orm.png'))

    # Everything ships as PNG. These maps are thin high-contrast lines on flat
    # fields: JPEG rings around them, which shows up as beading along the plank
    # joints and as speckle in the normal map.
    return [p('edge_lut.png'), p('deck_basecolor.png'), p('deck_normal.png'),
            p('deck_orm.png')]


# ---------------------------------------------------------------- export
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    rise = geometry.solve_rise()
    solid = geometry.build(rise)
    idx, pos, tags = solid.arrays()
    print('arch rise solved to %.6f  (deck crown y=%.4f, model height %.4f)'
          % (rise, float(geometry.deck(0.0, rise)), pos[:, 1].max()))
    print('assembled %d triangles from %d prisms' % (len(idx), len(idx) // 12))

    keep = np.ones(len(idx), bool)
    if cfg.BURIED['enabled']:
        _, buried = reshape.remove_buried_faces(idx, pos, cfg.BURIED)
        keep = ~buried
    if cfg.ZFIGHT['enabled']:
        survivors = np.nonzero(keep)[0]
        sub = reshape.drop_redundant_coplanar(idx[keep], pos, cfg.ZFIGHT)
        keep[survivors[~sub]] = False

    tri, fn, centroid = face_data(idx, pos)
    is_deck = select_deck(tags, fn) & keep

    welded, edges, angles, face_slots = sharp_convex_edges(idx, pos, fn, keep)
    uv1, overflow = build_uv1(idx, pos, welded, edges, angles, face_slots)
    uv0, pitch = build_uv0(idx, pos, fn, is_deck)
    normals = np.zeros_like(pos)
    normals[idx.reshape(-1)] = smooth_normals(idx, pos, fn,
                                              cfg.SHADING['smooth_deg'], keep)
    tangents = build_tangents(idx, pos, tri, fn, uv0, normals)

    print('faces: %d body / %d deck (%d buried or redundant dropped)'
          % ((keep & ~is_deck).sum(), is_deck.sum(), (~keep).sum()))
    print('sharp convex edges: %d' % len(edges))
    print('faces wanting a 3rd edge slot: %d' % overflow)

    images = prepare_textures(cfg.BUILD_DIR)

    # Applied last, and only to the exported positions: nudging faces before
    # edge detection separates vertices that used to be coincident, which
    # breaks the position welding the edge graph relies on. A pure translation
    # of a face changes none of the normals, tangents or UVs already computed.
    pos_out = (reshape.break_coplanar_ties(idx[keep], pos, cfg.ZFIGHT)
               if cfg.ZFIGHT['enabled'] else pos)

    w = GLBWriter()
    primitives = []
    for select, material in ((keep & ~is_deck, 0), (is_deck, 1)):
        v = idx[np.nonzero(select)[0]].reshape(-1)
        primitives.append({
            'attributes': {
                'POSITION':   w.add_f32(pos_out[v], 'VEC3'),
                'NORMAL':     w.add_f32(normals[v], 'VEC3'),
                'TANGENT':    w.add_f32(tangents[v], 'VEC4'),
                'TEXCOORD_0': w.add_f32(uv0[v], 'VEC2'),
                'TEXCOORD_1': w.add_f32(uv1[v], 'VEC2'),
            },
            'indices': w.add_indices(np.arange(len(v), dtype=np.uint32)),
            'mode': 4,
            'material': material,
        })

    gltf_images = [{'bufferView': w.add_image(f), 'mimeType': 'image/png',
                    'name': os.path.basename(f).rsplit('.', 1)[0]} for f in images]

    gltf = {
        'asset': {'version': '2.0', 'generator': 'bridge/build_bridge.py'},
        # lets the edge highlight exceed 1.0, so it can outrun the 0-1 ceiling
        # of an 8-bit emissive texture
        'extensionsUsed': ['KHR_materials_emissive_strength'],
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'name': 'bridge', 'mesh': 0}],
        'meshes': [{'name': 'bridge', 'primitives': primitives}],
        'samplers': [
            # deck: repeats along the span, clamps across the width
            {'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 33071},
            {'magFilter': 9729, 'minFilter': 9987, 'wrapS': 33071, 'wrapT': 33071},
            # The edge LUT is a ramp, not a picture. UV1 sweeps a huge range
            # across a single face, so the derivative is enormous and a mipmap
            # chain would collapse the whole falloff curve into its average.
            # LINEAR with no mips keeps the profile exact.
            {'magFilter': 9729, 'minFilter': 9729, 'wrapS': 33071, 'wrapT': 33071},
        ],
        'images': gltf_images,
        'textures': [{'sampler': 2, 'source': 0},        # edge LUT
                     {'sampler': 0, 'source': 1},        # deck basecolor
                     {'sampler': 0, 'source': 2},        # deck normal
                     {'sampler': 0, 'source': 3}],       # deck orm
        'materials': [
            {'name': 'dark_alloy', 'doubleSided': False,
             'pbrMetallicRoughness': {'baseColorFactor': cfg.BODY['base_color'],
                                      'metallicFactor': cfg.BODY['metallic'],
                                      'roughnessFactor': cfg.BODY['roughness']},
             # colour lives in the LUT; the factor is just a global dimmer
             'emissiveTexture': {'index': 0, 'texCoord': 1},
             'emissiveFactor': cfg.EDGES['emissive'],
             'extensions': {'KHR_materials_emissive_strength': {
                 'emissiveStrength': cfg.LUT['emissive_strength']}}},
            {'name': 'deck_plate', 'doubleSided': False,
             'pbrMetallicRoughness': {'baseColorTexture': {'index': 1},
                                      'metallicRoughnessTexture': {'index': 3},
                                      'metallicFactor': 0.0, 'roughnessFactor': 1.0},
             'normalTexture': {'index': 2, 'scale': cfg.DECK_MAT['normal_scale']},
             # the deck keeps its edge highlights: the plank grooves are where
             # most of them are
             'emissiveTexture': {'index': 0, 'texCoord': 1},
             'emissiveFactor': cfg.EDGES['emissive'],
             'extensions': {'KHR_materials_emissive_strength': {
                 'emissiveStrength': cfg.LUT['emissive_strength']}}},
        ],
    }

    total = w.write(cfg.OUTPUT_GLB, gltf)
    v = pos_out[idx[keep]].reshape(-1, 3)
    print('bounds %.4f x %.4f x %.4f  (drawing: %.2f x %.2f x %.2f)'
          % (*(v.max(0) - v.min(0)), cfg.ENVELOPE['length'],
             cfg.ENVELOPE['width'], cfg.ENVELOPE['height']))
    print('wrote %s  (%.2f MB, %d triangles)'
          % (cfg.OUTPUT_GLB, total / 1e6, int(keep.sum())))


if __name__ == '__main__':
    main()

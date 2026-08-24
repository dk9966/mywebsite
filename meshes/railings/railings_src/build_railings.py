"""Build the railing kit .glb from nothing but the numbers in config.py.

Run:  python build_railings.py

Pipeline, per module
--------------------
1. Assemble the module as a union of prisms (parts.py). Nothing is booleaned.
2. Delete the faces buried inside the union, then drop or nudge any
   coincident-surface ties that survive.
3. UV0 - triplanar. Unused by the flat materials, but it is what TANGENT is
         built against, so maps can be dropped in later without redoing UVs.
4. UV1 - per-vertex distance to the two nearest sharp convex edges. This is
         what produces the crisp edge highlight; see the note below.
5. Smoothed normals + tangents, then one primitive per material.

All five modules go into a single file as sibling nodes at the origin, so a
level editor fetches one asset and clones whichever node it needs.

Why the edge highlight works
----------------------------
Distance from a point to a straight edge is *linear* across a triangle, so it
interpolates exactly through the rasteriser -- no bake, no atlas, no seams, and
the line keeps a constant world-space width no matter how large the face is.
Two edges per triangle are encoded (u and v) and the LUT resolves them
together. Anything past the band clamps to zero via CLAMP_TO_EDGE sampling.

The lights are the one place this asset departs from bridge.glb, and they are
switched in config.LIGHTS. The lenses are always real geometry; turning a
channel off re-assigns their faces to the body material and drops the emissive
material from the file entirely, so the silhouette is identical either way.
"""
import os
from collections import defaultdict

import numpy as np

import config as cfg
import parts
import reshape
from glb import GLBWriter
from textures import make_edge_lut


# ---------------------------------------------------------------- geometry
def face_data(idx, pos):
    tri = pos[idx]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return tri, n, tri.mean(1)


def sharp_convex_edges(idx, pos, fn, keep=None):
    """Find the mesh's sharp convex edges.

    Returns (welded_positions, edge_list, angles, face_slots) where
    face_slots[f] is a list of (corner, edge_id) for that face.

    Detection runs on the *full* module even though buried faces are being
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

    The value stored is ``1 - d/w``: 1 right on the edge, 0 at the band limit,
    and negative past it, where CLAMP_TO_EDGE reads the LUT's zero border.
    Leaving it unclamped is what keeps it linear.

    Two slots per face. Where a triangle has more than two sharp convex edges
    the blunter ones lose, since a wide band is the one least missed.
    """
    e = cfg.EDGES
    if not len(edges):
        return np.zeros((len(pos), 2), np.float32), 0
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


def build_uv0(idx, pos, fn):
    """Triplanar projection, one tile per cfg.TILE world units.

    Nothing samples it today -- every material in this file is a flat colour
    plus the edge LUT, which rides on UV1. It exists because TANGENT has to be
    built against *some* parameterisation, and a triplanar one means a
    basecolor or normal map can be dropped onto the body later without
    re-authoring UVs or invalidating the tangents already in the file.
    """
    uv = np.zeros((len(pos), 2), np.float32)
    T = cfg.TILE
    axis = np.argmax(np.abs(fn), axis=1)
    for f in range(len(idx)):
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
    return uv


def smooth_normals(idx, pos, fn, threshold_deg, keep=None):
    """Per-vertex normals with smoothing groups.

    Almost every quad in this kit is perfectly planar, so unlike the bridge
    there is no sheared-facet artefact to fix. What this is actually for is the
    pillar's octagonal cap: its eight facets meet at 22.5 degrees, which under
    flat shading reads as a faceted nut rather than a turned cap. Averaging
    below the threshold rounds the ring while leaving every block joint on the
    model -- all of which bend far more than 26 degrees -- perfectly sharp.

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

    total = sum(1 for v in shared.values() if len(v) == 2)
    return normals.reshape(-1, 3), smooth_edges, total


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


# ---------------------------------------------------------------- materials
def material_plan():
    """Which glTF material index each face tag maps to, and the material list.

    A light channel that is switched off does not become a black material: its
    faces are re-assigned to the body material and the emissive material never
    enters the file. That keeps a lights-off build byte-comparable in structure
    to bridge.glb -- one material, no emissive tint -- rather than shipping a
    dead material that a downstream tool has to reason about.
    """
    E, L = cfg.EDGES, cfg.LUT
    mats = [{
        'name': 'dark_alloy', 'doubleSided': False,
        'pbrMetallicRoughness': {'baseColorFactor': cfg.BODY['base_color'],
                                 'metallicFactor': cfg.BODY['metallic'],
                                 'roughnessFactor': cfg.BODY['roughness']},
        # colour lives in the LUT; the factor is just a global dimmer
        'emissiveTexture': {'index': 0, 'texCoord': 1},
        'emissiveFactor': E['emissive'],
        'extensions': {'KHR_materials_emissive_strength': {
            'emissiveStrength': L['emissive_strength']}},
    }]
    tag_to_mat = {'body': 0, 'strip': 0, 'lamp': 0}

    def add(name, m):
        mats.append({
            'name': name, 'doubleSided': False,
            'pbrMetallicRoughness': {'baseColorFactor': m['base_color'],
                                     'metallicFactor': 0.0,
                                     'roughnessFactor': m['roughness']},
            # a flat lens, not an edge: no emissiveTexture, so the LUT cannot
            # draw a highlight down the middle of a light bar
            'emissiveFactor': m['emissive'],
            'extensions': {'KHR_materials_emissive_strength': {
                'emissiveStrength': m['emissive_strength']}},
        })
        return len(mats) - 1

    if cfg.LIGHTS['strips']:
        tag_to_mat['strip'] = add('strip_light', cfg.STRIP_MAT)
    if cfg.LIGHTS['lamp']:
        tag_to_mat['lamp'] = add('lamp_glass', cfg.LAMP_MAT)
    return tag_to_mat, mats


# ---------------------------------------------------------------- per module
def build_module(name, w, tag_to_mat):
    """Clean, parameterise and serialise one module. Returns a glTF mesh dict."""
    solid = parts.BUILDERS[name]()
    idx, pos, tags = solid.arrays()

    keep = np.ones(len(idx), bool)
    if cfg.BURIED['enabled']:
        _, buried = reshape.remove_buried_faces(idx, pos, cfg.BURIED)
        keep = ~buried
    if cfg.ZFIGHT['enabled']:
        survivors = np.nonzero(keep)[0]
        sub = reshape.drop_redundant_coplanar(idx[keep], pos, cfg.ZFIGHT)
        keep[survivors[~sub]] = False

    tri, fn, _ = face_data(idx, pos)
    welded, edges, angles, face_slots = sharp_convex_edges(idx, pos, fn, keep)
    uv1, overflow = build_uv1(idx, pos, welded, edges, angles, face_slots)
    uv0 = build_uv0(idx, pos, fn)
    vn, smoothed, shared = smooth_normals(idx, pos, fn,
                                          cfg.SHADING['smooth_deg'], keep)
    normals = np.zeros_like(pos)
    normals[idx.reshape(-1)] = vn
    tangents = build_tangents(idx, pos, tri, fn, uv0, normals)

    # Applied last, and only to the exported positions: nudging faces before
    # edge detection separates vertices that used to be coincident, which
    # breaks the position welding the edge graph relies on. A pure translation
    # of a face changes none of the normals, tangents or UVs already computed.
    pos_out = (reshape.break_coplanar_ties(idx[keep], pos, cfg.ZFIGHT)
               if cfg.ZFIGHT['enabled'] else pos)

    primitives = []
    for mat in sorted(set(tag_to_mat.values())):
        sel = keep & np.isin(tags, [t for t, m in tag_to_mat.items() if m == mat])
        if not sel.any():
            continue
        v = idx[np.nonzero(sel)[0]].reshape(-1)
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
            'material': mat,
        })

    v = pos_out[idx[keep]].reshape(-1, 3)
    lo, hi = v.min(0), v.max(0)
    print('  %-12s %4d tris (%3d dropped), %d sharp edges, '
          '%d/%d shared edges smoothed' % (name, int(keep.sum()), int((~keep).sum()),
                                           len(edges), smoothed, shared))
    print('  %-12s x [%+.3f, %+.3f]  y [%.3f, %.3f]  z [%+.3f, %+.3f]'
          % ('', lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    if overflow:
        print('  %-12s faces wanting a 3rd edge slot: %d' % ('', overflow))
    return {'name': name, 'primitives': primitives}, int(keep.sum())


# ---------------------------------------------------------------- export
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    tag_to_mat, materials = material_plan()
    print('lights: strips %s, lamp %s  ->  %d material(s)'
          % ('on' if cfg.LIGHTS['strips'] else 'off',
             'on' if cfg.LIGHTS['lamp'] else 'off', len(materials)))

    os.makedirs(cfg.BUILD_DIR, exist_ok=True)
    lut = make_edge_lut(os.path.join(cfg.BUILD_DIR, 'edge_lut.png'))

    w = GLBWriter()
    meshes, nodes, total_tris = [], [], 0
    for i, (name, note) in enumerate(cfg.NODES):
        mesh, n = build_module(name, w, tag_to_mat)
        meshes.append(mesh)
        total_tris += n
        nodes.append({'name': name, 'mesh': i,
                      'extras': {'pitch': cfg.PITCH, 'note': note}})

    gltf = {
        'asset': {'version': '2.0', 'generator': 'railings/build_railings.py',
                  'extras': {'pitch': cfg.PITCH, 'height': cfg.HEIGHT,
                             'grid': 'each module spans x [-0.5, +0.5]; '
                                     'terminals are centred on the node at x=+0.5'}},
        # lets the edge highlight and the lenses exceed 1.0, so they can outrun
        # the 0-1 ceiling of an 8-bit emissive texture / factor
        'extensionsUsed': ['KHR_materials_emissive_strength'],
        'scene': 0,
        'scenes': [{'nodes': list(range(len(nodes)))}],
        'nodes': nodes,
        'meshes': meshes,
        # The edge LUT is a ramp, not a picture. UV1 sweeps a huge range across
        # a single face, so the derivative is enormous and a mipmap chain would
        # collapse the whole falloff curve into its average. LINEAR with no
        # mips keeps the profile exact; CLAMP_TO_EDGE is what handles
        # everything outside the band.
        'samplers': [{'magFilter': 9729, 'minFilter': 9729,
                      'wrapS': 33071, 'wrapT': 33071}],
        'images': [{'bufferView': w.add_image(lut), 'mimeType': 'image/png',
                    'name': 'edge_lut'}],
        'textures': [{'sampler': 0, 'source': 0}],
        'materials': materials,
    }

    total = w.write(cfg.OUTPUT_GLB, gltf)
    print('wrote %s  (%.2f MB, %d nodes, %d triangles)'
          % (cfg.OUTPUT_GLB, total / 1e6, len(nodes), total_tris))


if __name__ == '__main__':
    main()

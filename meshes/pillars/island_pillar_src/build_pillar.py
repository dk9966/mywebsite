"""Build the island pillar .glb, geometry and texturing both procedural.

Run:  python build_pillar.py

Pipeline
--------
1. Generate the mesh (shape.py) -- shell, rim ring and brick paving, one
   watertight surface, already at the variant's final size.
2. UV0  - triplanar projection.
3. UV1  - per-vertex distance to the two nearest sharp convex edges. This is
          what produces the crisp edge highlight; see the note below.
4. Flat normals + tangents, one primitive, one material, one embedded LUT.

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
import cracks
import reshape
import shape
from glb import GLBWriter
from textures import make_edge_lut


# ---------------------------------------------------------------- geometry
def face_data(idx, pos):
    tri = pos[idx]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return tri, n, tri.mean(1)


def sharp_convex_edges(idx, pos, fn, keep=None, e=None):
    """Find the mesh's sharp convex edges.

    Returns (welded_positions, edge_list, angles, face_slots) where
    face_slots[f] is a list of (corner, edge_id) for that face. Everything
    downstream -- the glow path tracing and the UV1 packing -- works off this
    shared edge list.

    Detection runs on the *full* mesh even when buried faces are being dropped.
    Removing a face first would leave its neighbours' shared edges with only one
    adjacent face, so they would no longer register as creases at all: doing it
    the other way round cost half the edge graph and collapsed the glow runs
    from twelve to three. Edges are filtered afterwards, keeping only those with
    at least one surviving face.
    """
    welded, inv = np.unique(np.round(pos, 5), axis=0, return_inverse=True)
    F = inv[idx]
    shared = defaultdict(list)
    for f in range(len(F)):
        for k in range(3):
            a, b = F[f, k], F[f, (k + 1) % 3]
            shared[(min(a, b), max(a, b))].append((f, k))

    e = e or cfg.EDGES
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


def build_uv1(idx, pos, welded, edges, angles, face_slots, segs, face_seg, P):
    """Pack per-vertex edge distance, edge type *and* end-fade into UV1.

    Distance to a straight edge is linear across a triangle, so it interpolates
    exactly as a vertex attribute -- that is what makes these lines crisp with
    no bake and no atlas. The type is folded into the same number by mapping
    ordinary edges into the low part of the axis (peak inward, falling toward 0)
    and glow edges into the high part (peak inward, falling toward 1). Both run
    off the end of a texture border where the LUT is zero, so CLAMP_TO_EDGE
    handles everything beyond the band and the stored values can stay
    unclamped, and therefore linear.

    Fading a glow line toward the ends of its run needs no extra channel: the
    LUT profile already runs from full brightness at 0 to nothing at 1, so
    pushing the sample along that curve dims *and* thins the line by the same
    amount. The fade is added to the distance term rather than mixed with it --
    mixing would let a vertex past the end of the run report "band limit"
    regardless of how far it sits from the edge, which spreads the falloff
    across the whole face and floods it with light instead of drawing a line.

    The fade is evaluated at each vertex's projection onto the edge, not at the
    vertex itself, so all three vertices of a face agree on roughly where along
    the run they are. That keeps the stored value linear in distance, which is
    what keeps the line thin.
    """
    e = P['edges']
    pk, gk = cfg.LUT['plain_peak'], cfg.LUT['glow_peak']
    fade_len = P['glow']['fade']
    scale = np.clip((angles - e['angle_lo']) / (e['angle_hi'] - e['angle_lo']),
                    e['min_scale'], 1.0)

    uv1 = np.zeros((len(pos), 2), np.float32)
    overflow = 0
    for f in range(len(idx)):
        p = pos[idx[f]]
        lines = []                                 # (endpoints, width, span)

        si = face_seg[f]
        if si >= 0:                                # a crack claims slot 0
            a, b, y0, y1 = segs[si]
            lines.append((a, b, P['glow']['band'], (y0, y1)))

        for _, eid in face_slots[f]:               # then ordinary sharp edges
            lines.append((welded[edges[eid][0]], welded[edges[eid][1]],
                          e['band'] * scale[eid], None))

        if len(lines) > 2:
            overflow += 1
        for s, (a, b, w, span) in enumerate(lines[:2]):
            d = b - a
            d = d / (np.linalg.norm(d) + 1e-12)
            r = p - a
            r = r - np.outer(r @ d, d)             # perpendicular to the line
            t = np.linalg.norm(r, axis=1) / w      # 0 on the line, 1 at band limit
            if span is not None:
                y0, y1 = span
                # height of each vertex projected onto the segment
                u = np.clip((p - a) @ d, 0.0, np.linalg.norm(b - a))
                proj_y = a[1] + u * d[1]
                near_end = np.minimum(proj_y - y0, y1 - proj_y)
                fade = np.clip(1.0 - near_end / fade_len, 0.0, 1.0)
                uv1[idx[f], s] = gk + (1.0 - gk) * (t + fade)
            else:
                uv1[idx[f], s] = pk * (1.0 - t)
    return uv1, overflow


def build_uv0(idx, pos, fn, tile):
    """Triplanar projection for everything.

    The top paving used to be a separate primitive with a planar disc
    projection and its own textures; it is real geometry on the body material
    now, so one projection covers the whole pillar.
    """
    uv = np.zeros((len(pos), 2), np.float32)
    T = tile
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

    The mesh is built from quads, and hardware only draws triangles, so every
    quad is cut along a diagonal. Where a quad's four corners are not perfectly
    coplanar -- 904 edges here bend by between 0.001 and 25 degrees -- its two
    halves end up facing slightly different directions. Shaded flat, each half
    catches the light differently and the cut line shows up as a visible
    triangle.

    The fix is to average the normal across any edge whose bend is below
    ``threshold_deg``, so the two halves read as one continuous panel, while
    genuine creases above the threshold stay perfectly sharp.

    Only exported faces take part. Buried faces are interior and their
    orientation is arbitrary; averaging a visible normal with one of those
    corrupts the shading of a surface that looks fine.
    """
    if keep is None:
        keep = np.ones(len(idx), bool)
    welded, inv = np.unique(np.round(pos, 5), axis=0, return_inverse=True)
    W = inv[idx]

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

    # PNG: the LUT is a ramp, and JPEG rings around its hard boundaries.
    return [(p('edge_lut.png'), 'image/png')]


# ---------------------------------------------------------------- export
def scaled_params(width, height):
    """Config thresholds rewritten for a non-uniformly scaled pillar.

    Every world-unit number in config.py describes the base pillar. Once the
    mesh is stretched, heights have to follow `height`, radii follow `width`,
    and small feature sizes (band widths, probe distances, tie-break offsets)
    follow the geometric mean of the three axes -- they are not aligned to any
    single axis, and using width alone would make detail on the huge variant
    nearly twice as coarse as it should be.
    """
    detail = (width * width * height) ** (1.0 / 3.0)
    sc = lambda d, **kw: dict(d, **kw)
    return dict(
        detail=detail,
        buried=sc(cfg.BURIED, probe=cfg.BURIED['probe'] * detail),
        zfight=sc(cfg.ZFIGHT,
                  tolerance=cfg.ZFIGHT['tolerance'] * detail,
                  offset=cfg.ZFIGHT['offset'] * detail),
        top_cap=sc(cfg.TOP_CAP,
                   y_split=cfg.TOP_CAP['y_split'] * height,
                   haunch_band=tuple(v * height for v in cfg.TOP_CAP['haunch_band']),
                   outer_rmin=cfg.TOP_CAP['outer_rmin'] * width,
                   clearance=cfg.TOP_CAP['clearance'] * detail),
        edges=sc(cfg.EDGES, band=cfg.EDGES['band'] * detail),
        glow=sc(cfg.GLOW,
                band=cfg.GLOW['band'] * detail,
                offset=cfg.GLOW['offset'] * detail,
                plane_tol=cfg.GLOW['plane_tol'] * detail,
                step=cfg.GLOW['step'] * height,
                fade=cfg.GLOW['fade'] * height,
                min_extent=cfg.GLOW['min_extent'] * height,
                top_range=tuple(v * height for v in cfg.GLOW['top_range']),
                bottom_range=tuple(v * height for v in cfg.GLOW['bottom_range'])),
        tile=cfg.TILE * detail,
    )


def fill_profile(pos, fill, power):
    """Fatten the waist, leaving the ends where they are.

    The opposite of `flare_profile`. The multiplier is `1 + fill` at mid height
    and exactly 1.0 at both ends, so the pinch fills in and the pillar reads as
    a solid mass rather than an hourglass, without the top or bottom moving.
    """
    if not fill:
        return pos
    y = pos[:, 1]
    t = (y - y.min()) / (y.max() - y.min() + 1e-12)
    m = 1.0 + fill * (1.0 - np.abs(2.0 * t - 1.0) ** power)
    pos = pos.copy()
    pos[:, 0] *= m
    pos[:, 2] *= m
    return pos


def flare_profile(pos, flare, power):
    """Push the top and bottom outward, leaving the waist where it is.

    A plain width scale keeps the hourglass proportions fixed, so on a squat
    variant the flares read shallow. This multiplies radius by a factor that is
    1 + flare at both ends and 1.0 at mid height, which deepens the pinch
    without moving it.
    """
    if not flare:
        return pos
    y = pos[:, 1]
    t = (y - y.min()) / (y.max() - y.min() + 1e-12)
    m = 1.0 + flare * np.abs(2.0 * t - 1.0) ** power
    pos = pos.copy()
    pos[:, 0] *= m
    pos[:, 2] *= m
    return pos


def main(suffix='', width=1.0, height=1.0, flare=0.0, flare_power=None, grow=1.0,
         fill=0.0, fill_power=None):
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    P = scaled_params(width, height)

    # The stretch happens inside shape.build, not on the positions after: the
    # paving lays bricks of a fixed world size, so it must know the *final*
    # platform radius to lay more of them rather than bigger ones.
    idx, pos, mesh_info = shape.build(cfg.SHAPE, width, height)
    print('  shell: %d columns x %d rows, %s'
          % (mesh_info['columns'], mesh_info['rows'], shape.audit(idx, pos)))
    if (width, height) != (1.0, 1.0):
        print('  generated at width x%.2f, height x%.2f (detail x%.2f)'
              % (width, height, P['detail']))
    if fill:
        before = np.hypot(pos[:, 0], pos[:, 2])
        y = pos[:, 1]
        mid = (y > y.min() + 0.42 * (y.max() - y.min())) & (y < y.min() + 0.58 * (y.max() - y.min()))
        w0 = np.percentile(before[mid], 85)
        pos = fill_profile(pos, fill, fill_power or cfg.FILL_POWER)
        w1 = np.percentile(np.hypot(pos[:, 0], pos[:, 2])[mid], 85)
        # Measure the belly: how far the middle bows past the ends of its own
        # span. Positive and large means it reads as a barrel, not a column.
        #
        # Read at the 85th percentile of radius rather than the maximum. The
        # shell's ribs step in and out by a few percent block to block, so the
        # widest vertex in a band says which block happened to jut, not where
        # the silhouette runs -- on the maximum this reported a belly on a
        # pillar with no fill applied at all.
        rr = np.hypot(pos[:, 0], pos[:, 2])
        h = y.max() - y.min()
        band = lambda a, b: np.percentile(
            rr[(y >= y.min() + a * h) & (y < y.min() + b * h)], 85)
        bulge = band(0.42, 0.58) - min(band(0.30, 0.38), band(0.62, 0.70))
        print('  waist filled x%.2f (%.2f -> %.2f across, ends unchanged, '
              'mid bulge %+.3f)' % (1 + fill, 2 * w0, 2 * w1, bulge))
    if flare:
        # Flare, then renormalise the overall width back to the target. Without
        # this the flare inflates the widest point and the variant stops
        # matching the island size it is supposed to represent -- the huge one
        # came out 3.5x the base instead of 2.4x. Renormalising keeps the size
        # honest and turns the flare into a *deeper* hourglass rather than a
        # fatter pillar.
        target = np.hypot(pos[:, 0], pos[:, 2]).max() * grow
        pos = flare_profile(pos, flare, flare_power or cfg.FLARE_POWER)
        k = target / np.hypot(pos[:, 0], pos[:, 2]).max()
        pos[:, 0] *= k
        pos[:, 2] *= k
        print('  flared ends x%.2f, renormalised x%.3f (width x%.2f of target = %.2f)'
              % (1 + flare, k, grow, 2 * target))

    # widen_top_cap / remove_buried_faces / drop_redundant_coplanar all existed
    # to repair the old un-booleaned source mesh. The shell is watertight and
    # has no interior faces at all, so they are off by default -- see reshape.py.
    if P['top_cap']['enabled']:
        pos, _ = reshape.widen_top_cap(pos, P['top_cap'], idx)
    keep = np.ones(len(idx), bool)
    if P['buried']['enabled']:
        _, buried = reshape.remove_buried_faces(idx, pos, P['buried'])
        keep = ~buried
    if P['zfight']['enabled']:
        survivors = np.nonzero(keep)[0]
        sub = reshape.drop_redundant_coplanar(idx[keep], pos, P['zfight'])
        keep[survivors[~sub]] = False
    tri, fn, centroid = face_data(idx, pos)

    welded, edges, angles, face_slots = sharp_convex_edges(idx, pos, fn, keep,
                                                           P['edges'])
    paths = cracks.generate(pos, idx[keep], P['glow'])
    segs = cracks.segments(paths)
    face_seg = np.full(len(idx), -1)
    face_seg[keep] = cracks.assign_to_faces(pos, idx[keep], segs,
                                            P['glow']['band'], P['glow']['plane_tol'])
    uv1, overflow = build_uv1(idx, pos, welded, edges, angles, face_slots,
                              segs, face_seg, P)
    uv0 = build_uv0(idx, pos, fn, P['tile'])
    normals = np.zeros_like(pos)
    normals[idx.reshape(-1)] = smooth_normals(idx, pos, fn,
                                              cfg.SHADING['smooth_deg'], keep)
    tangents = build_tangents(idx, pos, tri, fn, uv0, normals)

    print('faces: %d, one material -- the paving is geometry now, not a texture'
          % keep.sum())
    print('sharp convex edges: %d' % len(edges))
    print('faces wanting a 3rd edge slot: %d' % overflow)

    images = prepare_textures(cfg.BUILD_DIR)

    # Applied last, and only to the exported positions: nudging faces before
    # edge detection separates vertices that used to be coincident, which
    # breaks the position welding the edge graph relies on and silently costs
    # several hundred creases. A pure translation of a face changes none of the
    # normals, tangents or UVs already computed.
    pos_out = (reshape.break_coplanar_ties(idx[keep], pos, P['zfight'])
               if P['zfight']['enabled'] else pos)

    w = GLBWriter()
    v = idx[np.nonzero(keep)[0]].reshape(-1)
    primitives = [{
        'attributes': {
            'POSITION':   w.add_f32(pos_out[v], 'VEC3'),
            'NORMAL':     w.add_f32(normals[v], 'VEC3'),
            'TANGENT':    w.add_f32(tangents[v], 'VEC4'),
            'TEXCOORD_0': w.add_f32(uv0[v], 'VEC2'),
            'TEXCOORD_1': w.add_f32(uv1[v], 'VEC2'),
        },
        'indices': w.add_indices(np.arange(len(v), dtype=np.uint32)),
        'mode': 4,
        'material': 0,
    }]

    gltf_images = [{'bufferView': w.add_image(f), 'mimeType': m,
                    'name': os.path.basename(f).rsplit('.', 1)[0]} for f, m in images]

    gltf = {
        'asset': {'version': '2.0', 'generator': 'island-pillar/build_pillar.py'},
        # lets emissive exceed 1.0 so the glow lines can outrun the 0-1 ceiling
        # of an 8-bit emissive texture
        'extensionsUsed': ['KHR_materials_emissive_strength'],
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'name': 'island_pillar', 'mesh': 0}],
        'meshes': [{'name': 'island_pillar', 'primitives': primitives}],
        'samplers': [
            # The edge LUT is a ramp, not a picture. UV1 sweeps a huge range
            # across a single face, so the derivative is enormous and a mipmap
            # chain would collapse the whole falloff curve into its average --
            # and blur the two profiles into each other across the dead zone.
            # LINEAR with no mips keeps the profile exact.
            {'magFilter': 9729, 'minFilter': 9729, 'wrapS': 33071, 'wrapT': 33071},
        ],
        'images': gltf_images,
        'textures': [{'sampler': 0, 'source': 0}],                      # edge LUT
        # One material for everything, top paving included -- the paving is
        # geometry now, and its joint lines come from the same edge highlight
        # as the block outlines on the shaft.
        'materials': [
            {'name': 'dark_slate_edges', 'doubleSided': False,
             'pbrMetallicRoughness': {'baseColorFactor': cfg.BODY['base_color'],
                                      'metallicFactor': cfg.BODY['metallic'],
                                      'roughnessFactor': cfg.BODY['roughness']},
             # colour lives in the LUT so ordinary and glow edges can differ;
             # the factor is just a global dimmer for both
             'emissiveTexture': {'index': 0, 'texCoord': 1},
             'emissiveFactor': cfg.EDGES['emissive'],
             'extensions': {'KHR_materials_emissive_strength': {
                 'emissiveStrength': cfg.LUT['emissive_strength']}}},
        ],
    }

    out_path = cfg.OUTPUT_GLB.replace('.glb', suffix + '.glb')
    total = w.write(out_path, gltf)
    print('wrote %s  (%.2f MB, %d triangles, %.1f tall)'
          % (out_path, total / 1e6, int(keep.sum()),
             (pos_out[:, 1].max() - pos_out[:, 1].min())))


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        for v in cfg.VARIANTS:
            print('--- %s (width x%.2f, height x%.2f, fill %.2f, flare %.2f)'
                  % (v['suffix'] or 'base', v['width'], v['height'],
                     v.get('fill', 0.0), v.get('flare', 0.0)))
            main(v['suffix'], v['width'], v['height'], v.get('flare', 0.0),
                 v.get('flare_power'), v.get('grow', 1.0),
                 v.get('fill', 0.0), v.get('fill_power'))
    else:
        main()

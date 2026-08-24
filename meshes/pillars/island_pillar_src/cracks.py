"""Generate glowing crack paths across the pillar surface.

Why this exists
---------------
The first version lit up the mesh's own sharp edges. That was the wrong shape
of thing. A mesh edge is by definition the *boundary between two faces*, so an
edge-locked line can only ever trace the outline of the blocks -- it reads as
glowing trim on the corners, it zigzags with whatever tessellation the modeller
happened to use, and on a convex corner you see it edge-on from most angles.

The reference art does the opposite: its cracks run *across* faces, straight for
long stretches, jogging sideways occasionally, ignoring the geometry underneath.

So the cracks here are generated as free polylines lying on the surface, with no
relationship to the triangles. They still get drawn by the same UV1 distance
packing as the edge highlights -- that machinery never cared whether a line was
a real edge, only that it is a straight segment in space -- so they stay crisp
at any zoom and keep a constant world-space width.
"""
import numpy as np


def surface_radius_field(pos, faces, n_ang, n_y, y_range):
    """Grid of the outer radius of the model over (angle, height).

    Sampled from vertices, then dilated to fill the gaps between them, so a
    crack point can be placed on the surface at any angle and height.
    """
    v = pos[faces].reshape(-1, 3)
    r = np.hypot(v[:, 0], v[:, 2])
    ang = np.arctan2(v[:, 2], v[:, 0]) % (2 * np.pi)
    y0, y1 = y_range

    ai = np.clip((ang / (2 * np.pi) * n_ang).astype(int), 0, n_ang - 1)
    yi = np.clip(((v[:, 1] - y0) / (y1 - y0) * n_y).astype(int), 0, n_y - 1)

    grid = np.full((n_ang, n_y), -np.inf)
    np.maximum.at(grid, (ai, yi), r)

    # dilate into empty cells so the field is defined everywhere
    for _ in range(24):
        if np.isfinite(grid).all():
            break
        g = grid
        grid = np.maximum.reduce([
            g,
            np.roll(g, 1, 0), np.roll(g, -1, 0),
            np.concatenate([g[:, :1], g[:, :-1]], 1),
            np.concatenate([g[:, 1:], g[:, -1:]], 1),
        ])
    grid[~np.isfinite(grid)] = np.nanmax(grid[np.isfinite(grid)])
    return grid


def _sample(grid, theta, y, y_range):
    n_ang, n_y = grid.shape
    y0, y1 = y_range
    ai = int(theta / (2 * np.pi) * n_ang) % n_ang
    yi = int(np.clip((y - y0) / (y1 - y0) * n_y, 0, n_y - 1))
    return grid[ai, yi]


def _closest_on_triangles(q, tri):
    """Closest point on a triangle soup to a single query point."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    ab, ac, ap = b - a, c - a, q - a
    n = np.cross(ab, ac)
    nn = np.einsum('ij,ij->i', n, n) + 1e-18
    # barycentric coordinates of the projection, then clamped into the triangle
    v = np.einsum('ij,ij->i', np.cross(ap, ac), n) / nn
    w = np.einsum('ij,ij->i', np.cross(ab, ap), n) / nn
    u = 1.0 - v - w
    inside = (u >= 0) & (v >= 0) & (w >= 0)
    p = a + v[:, None] * ab + w[:, None] * ac

    if not inside.all():                       # clamp the rest onto the edges
        out = ~inside
        best = None
        for e0, e1 in ((a, b), (b, c), (c, a)):
            d = e1 - e0
            t = np.clip(np.einsum('ij,ij->i', q - e0, d)
                        / (np.einsum('ij,ij->i', d, d) + 1e-18), 0, 1)
            cand = e0 + t[:, None] * d
            dist = np.linalg.norm(cand - q, axis=1)
            if best is None:
                best, bestd = cand, dist
            else:
                take = dist < bestd
                best = np.where(take[:, None], cand, best)
                bestd = np.minimum(dist, bestd)
        p = np.where(out[:, None], best, p)
    return p


def snap_to_surface(points, tri, normals, offset):
    """Move each crack point onto the nearest real surface.

    Placing points at the outer radius alone leaves a path floating in mid-air
    wherever it crosses a recessed channel, and the line simply disappears
    there. Snapping to the mesh keeps it lying on something.
    """
    out = np.empty_like(points)
    for i, q in enumerate(points):
        near = np.linalg.norm(tri.mean(1) - q, axis=1) < 0.75
        if not near.any():
            near = np.ones(len(tri), bool)
        cand = _closest_on_triangles(q, tri[near])
        d = np.linalg.norm(cand - q, axis=1)
        j = int(np.argmin(d))
        out[i] = cand[j] + normals[near][j] * offset
    return out


def generate(pos, faces, params):
    """-> list of paths, each a list of 3D points lying on the surface.

    A path walks downward in short steps, occasionally stepping sideways by a
    few degrees and then carrying on down. That produces the long straight runs
    with clean jogs that the reference has, rather than the wander you get from
    following mesh connectivity.
    """
    if params['paths'] <= 0:
        print('  cracks: disabled (GLOW.paths = 0)')
        return []

    rng = np.random.default_rng(params['seed'])
    y_range = (float(pos[:, 1].min()), float(pos[:, 1].max()))
    grid = surface_radius_field(pos, faces, params['field_angles'],
                                params['field_heights'], y_range)

    paths = []
    n = params['paths']
    for i in range(n):
        # spread the starts evenly, then jitter so they are not a perfect ring
        theta = (i + rng.uniform(0.2, 0.8)) / n * 2 * np.pi
        top = rng.uniform(*params['top_range'])
        bottom = rng.uniform(*params['bottom_range'])
        if top - bottom < params['min_extent']:
            continue

        pts = []
        y = top
        while y > bottom:
            r = _sample(grid, theta, y, y_range) + params['offset']
            pts.append([r * np.cos(theta), y, r * np.sin(theta)])
            if rng.random() < params['jog_chance']:
                # step sideways at constant height, then resume descending
                theta += np.radians(rng.uniform(*params['jog_degrees'])
                                    * rng.choice([-1.0, 1.0]))
                r = _sample(grid, theta, y, y_range) + params['offset']
                pts.append([r * np.cos(theta), y, r * np.sin(theta)])
            y -= params['step']

        r = _sample(grid, theta, bottom, y_range) + params['offset']
        pts.append([r * np.cos(theta), bottom, r * np.sin(theta)])
        paths.append(np.array(pts))

    if not paths:
        print('  cracks: none met the minimum extent')
        return []

    tri = pos[faces]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
    paths = [snap_to_surface(p, tri, fn, params['offset']) for p in paths]

    total = sum(len(p) - 1 for p in paths)
    spans = [(p[:, 1].min(), p[:, 1].max()) for p in paths]
    print('  cracks: %d paths, %d segments, spanning y %.2f-%.2f'
          % (len(paths), total,
             min(s[0] for s in spans), max(s[1] for s in spans)))
    return paths


def segments(paths):
    """Flatten paths into (a, b, path_y_min, path_y_max) tuples."""
    out = []
    for p in paths:
        lo, hi = float(p[:, 1].min()), float(p[:, 1].max())
        for a, b in zip(p[:-1], p[1:]):
            if np.linalg.norm(b - a) > 1e-9:
                out.append((a, b, lo, hi))
    return out


def assign_to_faces(pos, faces, segs, reach, plane_tol):
    """Which crack segment, if any, each face should carry.

    A face qualifies when part of it lies within ``reach`` of the segment *and*
    the segment sits close to that face's own plane. The plane test is what
    stops a crack on one rib lighting up the face of the rib behind it.
    """
    if not segs:
        return np.full(len(faces), -1)

    tri = pos[faces]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
    d0 = np.einsum('ij,ij->i', fn, tri[:, 0])

    best = np.full(len(faces), -1)
    best_dist = np.full(len(faces), np.inf)

    for si, (a, b, _, _) in enumerate(segs):
        ab = b - a
        L2 = float(ab @ ab)
        mid = (a + b) * 0.5
        # distance from every vertex to the segment
        rel = tri.reshape(-1, 3) - a
        t = np.clip((rel @ ab) / max(L2, 1e-12), 0.0, 1.0)
        closest = a + t[:, None] * ab
        dist = np.linalg.norm(tri.reshape(-1, 3) - closest, axis=1).reshape(-1, 3)
        dmin = dist.min(1)

        near = dmin < reach
        if not near.any():
            continue
        # the crack must lie roughly in this face's plane, not on a face behind
        near &= np.abs(fn @ mid - d0) < plane_tol
        near &= dmin < best_dist
        if not near.any():
            continue
        best[near] = si
        best_dist[near] = dmin[near]

    print('  cracks assigned to %d faces' % int((best >= 0).sum()))
    return best

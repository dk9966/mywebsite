"""Repairs for an imported mesh, applied in memory before texturing.

None of these run any more, and the flags in config.py have them off. They exist
for a mesh that arrives as a union of un-booleaned boxes, which is what this
pillar used to be. shape.py now generates the pillar as one watertight surface
with no interior faces, no coincident planes and no separate cap object, so
there is nothing here left to fix -- see shape.py's header for why building the
surface rather than the solid removes all three problems at once.

They are kept because they still work, and because a future imported part might
need them. Everything below describes the problem each one solved.

Removing buried faces
---------------------
The source mesh is a pile of overlapping boxes that were never booleaned
together, so faces sit *inside* the solid, exactly coplanar with visible ones.
Two surfaces at the same depth flicker against each other -- classic
z-fighting, which reads as sparkling or "aliasing" that no amount of
anti-aliasing will fix. They are found with a generalized winding number and
deleted.

Breaking coincident-surface ties
--------------------------------
Some faces survive burial removal and are still exactly coplanar and coincident
with another visible face -- two boxes butted flush share a wall. Neither is
inside the solid, so neither can be deleted, but at identical depth the two
flicker against each other as the camera moves. Nudging one of each pair inward
by a hair gives the depth test a stable winner.

Widening the top cap
--------------------
The pillar's top outward flare ("haunch") reaches a larger radius than the
crenellation ring sitting above it, so at some angles the haunch's corners poke
out past the top and break the silhouette. Scaling the cap outward in XZ until
it covers the haunch everywhere turns those corners into an overhang and hides
them.

The scale is not a magic number: it is derived from the geometry as the smallest
factor that clears the haunch at every angle, plus a margin. Change the mesh and
it recomputes.
"""
import numpy as np


def _outer_profile(pos, mask, bins, min_radius, faces=None):
    """Max radius per angular bin.

    Binning by vertex misses a face whose vertices land in neighbouring bins but
    whose surface spans the bin between them -- that reported a false exposure
    at two angles here. When ``faces`` is given the coverage is computed from
    the triangles instead, so every bin a face spans is accounted for.
    """
    r = np.hypot(pos[:, 0], pos[:, 2])
    ang = np.degrees(np.arctan2(pos[:, 2], pos[:, 0])) % 360
    out = np.full(bins, np.nan)

    if faces is None:
        sel = mask & (r > min_radius)
        b = (ang[sel] / 360 * bins).astype(int) % bins
        rr = r[sel]
        for i in range(bins):
            m = b == i
            if m.any():
                out[i] = rr[m].max()
        return out

    for f in faces:
        if not mask[f].all():
            continue
        rf = r[f]
        if rf.max() <= min_radius:
            continue
        a = ang[f]
        a = np.where(a - a[0] > 180, a - 360,
                     np.where(a - a[0] < -180, a + 360, a))
        i0 = int(np.floor(a.min() / 360 * bins))
        i1 = int(np.ceil(a.max() / 360 * bins))
        for i in range(i0, i1 + 1):
            j = i % bins
            out[j] = rf.max() if np.isnan(out[j]) else max(out[j], rf.max())
    return out


def top_cap_scale(pos, params, faces=None):
    """Smallest uniform XZ scale that lifts the cap clear of the haunch."""
    y = pos[:, 1]
    bins = params['bins']
    lo, hi = params['haunch_band']
    haunch = _outer_profile(pos, (y > lo) & (y < hi), bins, params['outer_rmin'], faces)
    cap = _outer_profile(pos, y >= params['y_split'], bins, params['outer_rmin'], faces)
    ok = ~np.isnan(haunch) & ~np.isnan(cap)
    if not ok.any():
        raise ValueError('no overlapping angular bins between haunch and cap')
    needed = (haunch[ok] + params['clearance']) / cap[ok]
    return max(1.0, float(needed.max())), haunch, cap


def widen_top_cap(pos, params, faces=None):
    """Scale the top cap outward so the haunch corners sit underneath it."""
    pos = pos.copy()
    k, haunch, cap = top_cap_scale(pos, params, faces)
    sel = pos[:, 1] >= params['y_split']
    before = np.hypot(pos[sel, 0], pos[sel, 2]).max()
    pos[sel, 0] *= k
    pos[sel, 2] *= k
    after = np.hypot(pos[sel, 0], pos[sel, 2]).max()
    exposed = int((np.nan_to_num(cap * k, nan=np.inf)
                   < np.nan_to_num(haunch, nan=-np.inf)).sum())
    print('  top cap widened x%.4f (outer r %.3f -> %.3f), '
          'haunch max r %.3f, angles still exposed: %d'
          % (k, before, after, np.nanmax(haunch), exposed))
    return pos, k


def _winding_numbers(queries, tri, chunk=256):
    """Generalized winding number of a triangle soup at each query point.

    Plain ray-parity does not work here: the mesh is a union of overlapping
    closed shells, and a point inside two of them gets an even crossing count
    and is misread as outside. The winding number sums signed solid angles
    instead, so a point inside k shells scores k and stays >= 1.
    """
    a_all, b_all, c_all = tri[:, 0], tri[:, 1], tri[:, 2]
    out = np.empty(len(queries))
    for s in range(0, len(queries), chunk):
        q = queries[s:s + chunk][:, None, :]
        a = a_all[None] - q
        b = b_all[None] - q
        c = c_all[None] - q
        la = np.linalg.norm(a, axis=-1)
        lb = np.linalg.norm(b, axis=-1)
        lc = np.linalg.norm(c, axis=-1)
        num = np.einsum('qti,qti->qt', a, np.cross(b, c))
        den = (la * lb * lc
               + np.einsum('qti,qti->qt', a, b) * lc
               + np.einsum('qti,qti->qt', b, c) * la
               + np.einsum('qti,qti->qt', c, a) * lb)
        out[s:s + chunk] = np.arctan2(num, den).sum(1) * 2.0
    return out / (4.0 * np.pi)


def remove_buried_faces(idx, pos, params):
    """Drop faces that sit inside the solid rather than on its surface.

    A surface face has solid on one side and open space on the other. A buried
    face has solid on *both* sides. Testing both sides rather than just the
    outward one matters here because the mesh has inconsistently wound
    triangles: testing only along +normal deletes any correctly-placed face
    that happens to be wound inward, which is how the entire underside of the
    plinth disappeared.

    The test samples the whole face, not just the centroid. Faces here are
    routinely half-embedded (a rib sunk into the core cylinder), and a
    centroid-only test deletes those outright, punching holes in the model.
    Requiring *every* sample to be buried keeps anything partly visible.
    """
    tri = pos[idx]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    norm = np.linalg.norm(n, axis=1, keepdims=True)
    degenerate = norm[:, 0] < 1e-12
    n = n / (norm + 1e-18)

    centroid = tri.mean(1)
    samples = [centroid]
    for k in range(3):
        samples.append(tri[:, k] * 0.80 + centroid * 0.20)          # near each corner
        samples.append((tri[:, k] + tri[:, (k + 1) % 3]) * 0.40 + centroid * 0.20)
    eps = params['probe']

    buried = ~degenerate
    for side in (1.0, -1.0):
        for pts in samples:
            if not buried.any():
                break
            w = _winding_numbers(pts + n * (eps * side), tri)
            buried &= w > params['threshold']

    print('  buried faces removed: %d of %d (%.1f%%)'
          % (buried.sum(), len(idx), 100.0 * buried.sum() / len(idx)))
    return idx[~buried], buried


def _coplanar_overlaps(idx, pos, tol):
    """Pairs of coincident, same-facing, genuinely overlapping faces."""
    tri = pos[idx]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(cross, axis=1)
    n = cross / (np.linalg.norm(cross, axis=1, keepdims=True) + 1e-18)

    def overlap(a2, b2):
        for poly, other in ((a2, b2), (b2, a2)):
            for i in range(3):
                e = poly[(i + 1) % 3] - poly[i]
                ax = np.array([-e[1], e[0]])
                pa, pb = poly @ ax, other @ ax
                if pa.min() >= pb.max() - 1e-9 or pb.min() >= pa.max() - 1e-9:
                    return False
        return True

    verts = [set(map(tuple, np.round(t, 5))) for t in tri]
    buckets = {}
    for i in range(len(idx)):
        if area[i] < 1e-9:
            continue
        nd = n[i] if n[i][np.argmax(np.abs(n[i]))] >= 0 else -n[i]
        key = (tuple(np.round(nd, 2)), round(abs(float(n[i] @ tri[i, 0])), 3))
        buckets.setdefault(key, []).append(i)

    pairs = []
    for faces in buckets.values():
        if len(faces) < 2:
            continue
        ax = int(np.argmax(np.abs(n[faces[0]])))
        keep = [k for k in range(3) if k != ax]
        flat = {i: tri[i][:, keep] for i in faces}
        for a in range(len(faces)):
            for b in range(a + 1, len(faces)):
                fa, fb = faces[a], faces[b]
                if len(verts[fa] & verts[fb]) >= 2:      # shares an edge
                    continue
                if float(n[fa] @ n[fb]) < 0.5:           # back-to-back, not a tie
                    continue
                sep = abs(float(n[fa] @ tri[fa, 0]) - float(n[fa] @ tri[fb, 0]))
                if sep > tol:
                    continue
                if overlap(flat[fa], flat[fb]):
                    pairs.append((fa, fb))
    return pairs, n, area


def _contained(small, big, tri, n):
    """Is triangle `small` fully inside triangle `big`, in their shared plane?"""
    ax = int(np.argmax(np.abs(n[big])))
    keep = [k for k in range(3) if k != ax]
    v0, v1, v2 = tri[big][:, keep]
    d = (v1[1] - v2[1]) * (v0[0] - v2[0]) + (v2[0] - v1[0]) * (v0[1] - v2[1])
    if abs(d) < 1e-12:
        return False
    for p in tri[small][:, keep]:
        a = ((v1[1] - v2[1]) * (p[0] - v2[0]) + (v2[0] - v1[0]) * (p[1] - v2[1])) / d
        b = ((v2[1] - v0[1]) * (p[0] - v2[0]) + (v0[0] - v2[0]) * (p[1] - v2[1])) / d
        if min(a, b, 1 - a - b) < -1e-6:
            return False
    return True


def drop_redundant_coplanar(idx, pos, params):
    """Delete faces wholly contained inside a coincident coplanar neighbour.

    Deleting beats nudging when it applies: the face contributes nothing the
    larger one does not already cover, so there is nothing left to flicker.
    """
    pairs, n, area = _coplanar_overlaps(idx, pos, params['tolerance'])
    tri = pos[idx]
    drop = set()
    for fa, fb in pairs:
        small, big = (fa, fb) if area[fa] <= area[fb] else (fb, fa)
        if small in drop or big in drop:
            continue
        if _contained(small, big, tri, n):
            drop.add(small)
    mask = np.ones(len(idx), bool)
    mask[list(drop)] = False
    print('  redundant coplanar faces dropped: %d' % len(drop))
    return mask


def break_coplanar_ties(idx, pos, params):
    """Offset one face of each coincident pair so the depth test is stable.

    Vertices are split per face in this mesh, so moving one face does not drag
    its neighbours with it. The offset is far below anything visible; it exists
    only to stop two surfaces at identical depth from flickering.

    Repeated until clean: a face can be the loser of several pairs at once, and
    moving it resolves only one of them per pass.
    """
    pos = pos.copy()
    total = 0
    for _ in range(params['passes']):
        pairs, n, area = _coplanar_overlaps(idx, pos, params['tolerance'])
        if not pairs:
            break
        moved = set()
        for fa, fb in pairs:
            loser = fa if area[fa] <= area[fb] else fb   # nudge the smaller face
            if loser in moved:
                continue
            pos[idx[loser]] -= n[loser] * params['offset']
            moved.add(loser)
        total += len(moved)
    remaining = len(_coplanar_overlaps(idx, pos, params['tolerance'])[0])
    print('  coincident coplanar pairs resolved by nudging %d faces; %d left'
          % (total, remaining))
    return pos

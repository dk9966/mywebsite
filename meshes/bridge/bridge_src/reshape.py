"""Cleanup passes applied to the assembled bridge before texturing.

Removing buried faces
---------------------
The bridge is a pile of overlapping prisms that were never booleaned together,
so faces sit *inside* the solid, many exactly coplanar with visible ones. Two
surfaces at the same depth flicker against each other -- classic z-fighting,
which reads as sparkling that no amount of anti-aliasing will fix. They are
found with a generalized winding number and deleted.

Breaking coincident-surface ties
--------------------------------
Some faces survive burial removal and are still exactly coplanar and coincident
with another visible face -- two prisms butted flush share a wall. Neither is
inside the solid, so neither can be deleted, but at identical depth the two
flicker as the camera moves. Nudging one of each pair inward by a hair gives
the depth test a stable winner.

This is the island pillar's module with the pillar-specific top-cap reshaping
dropped, and one change: the winding-number passes now re-test only the faces
still in the running rather than the whole mesh every time. On a model this
segmented that is the difference between a couple of seconds and a minute.
"""
import numpy as np


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
    outward one matters because a triangle soup assembled this way has no
    guarantee of consistent winding: testing only along +normal deletes any
    correctly-placed face that happens to be wound inward.

    The test samples the whole face, not just the centroid. Parts here are
    routinely half-embedded -- a plank sunk into the slab, the slab running into
    an abutment plinth -- and a centroid-only test deletes those outright,
    punching holes. Requiring *every* sample to be buried keeps anything partly
    visible. Note that this is a necessary condition and not a sufficient one:
    see geometry.slab_edges for the case where all fourteen probes agreed and
    were all wrong.
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

    # Only faces still under suspicion get re-tested. The first pass eliminates
    # the overwhelming majority, so every later pass is nearly free.
    live = np.nonzero(~degenerate)[0]
    for side in (1.0, -1.0):
        for pts in samples:
            if not len(live):
                break
            w = _winding_numbers(pts[live] + n[live] * (eps * side), tri)
            live = live[w > params['threshold']]

    buried = np.zeros(len(idx), bool)
    buried[live] = True
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

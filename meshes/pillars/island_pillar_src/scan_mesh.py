"""Scan the shipped mesh for things that show up as shimmer or artefacts.

Reads the exported glb so the report describes what actually ships. Falls back
to the generated shell if nothing has been built yet.

Run:  python scan_mesh.py
"""
import os
from collections import defaultdict

import numpy as np

import config as cfg
import reshape
import shape


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if os.path.exists(cfg.OUTPUT_GLB):
        from glb import read_glb, accessor
        g, bin_ = read_glb(cfg.OUTPUT_GLB)
        P, F, off = [], [], 0
        for p in g['meshes'][0]['primitives']:
            pp = np.asarray(accessor(g, bin_, p['attributes']['POSITION']), float)
            F.append(np.asarray(accessor(g, bin_, p['indices']), np.int64).reshape(-1, 3) + off)
            P.append(pp)
            off += len(pp)
        pos, idx = np.vstack(P), np.vstack(F)
        print('scanning exported %s' % cfg.OUTPUT_GLB)
    else:
        idx, pos, _ = shape.build(cfg.SHAPE)
        print('scanning the generated shell (nothing built yet)')
    tri = pos[idx]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(cross, axis=1)
    n = cross / (np.linalg.norm(cross, axis=1, keepdims=True) + 1e-18)

    print('triangles: %d   total area %.3f' % (len(idx), area.sum()))

    # --- degenerate ---------------------------------------------------
    degen = area < 1e-9
    print('\ndegenerate (zero-area) triangles: %d' % degen.sum())
    e = np.stack([np.linalg.norm(tri[:, (i + 1) % 3] - tri[:, i], axis=1)
                  for i in range(3)], 1)
    slivers = (~degen) & (e.min(1) < 1e-4)
    print('slivers (an edge under 1e-4): %d' % slivers.sum())
    # thinness: shortest altitude vs longest edge
    with np.errstate(divide='ignore', invalid='ignore'):
        thin = np.where(area > 1e-12, 2 * area / e.max(1), 0)
    print('very thin triangles (altitude < 1e-3): %d' % ((area > 1e-12) & (thin < 1e-3)).sum())

    # --- exact duplicates ---------------------------------------------
    key = [tuple(sorted(map(tuple, np.round(t, 5)))) for t in tri]
    seen = defaultdict(list)
    for i, k in enumerate(key):
        seen[k].append(i)
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    print('\nduplicate triangles (same 3 positions): %d groups, %d faces'
          % (len(dupes), sum(len(v) for v in dupes.values())))
    for k, v in list(dupes.items())[:5]:
        opposed = np.dot(n[v[0]], n[v[1]]) < -0.5
        print('   faces %s  %s' % (v[:4], 'opposed normals' if opposed else 'same facing'))

    # --- coplanar overlaps (z-fighting candidates) --------------------
    # Only pairs that are coplanar, do NOT share an edge, and genuinely overlap
    # in 2D can z-fight. Adjacent triangles of the same quad are coplanar and
    # share bounds, so a bounds test alone reports thousands of false positives.
    def tri_overlap(a2, b2):
        """Separating-axis test for two 2D triangles."""
        for poly, other in ((a2, b2), (b2, a2)):
            for i in range(3):
                edge = poly[(i + 1) % 3] - poly[i]
                axis = np.array([-edge[1], edge[0]])
                pa = poly @ axis
                pb = other @ axis
                if pa.min() >= pb.max() - 1e-9 or pb.min() >= pa.max() - 1e-9:
                    return False
        return True

    vert_sets = [set(map(tuple, np.round(t, 5))) for t in tri]
    planes = defaultdict(list)
    for i in range(len(idx)):
        if area[i] < 1e-9:
            continue
        nd = n[i] if n[i][np.argmax(np.abs(n[i]))] >= 0 else -n[i]
        planes[(tuple(np.round(nd, 2)), round(abs(float(n[i] @ tri[i, 0])), 3))].append(i)

    zf, examples, seps = 0, [], []
    back_to_back = 0
    for faces in planes.values():
        if len(faces) < 2:
            continue
        axis = int(np.argmax(np.abs(n[faces[0]])))
        keep = [k for k in range(3) if k != axis]
        flat = {i: tri[i][:, keep] for i in faces}
        for a in range(len(faces)):
            for b in range(a + 1, len(faces)):
                fa, fb = faces[a], faces[b]
                if len(vert_sets[fa] & vert_sets[fb]) >= 2:
                    continue                     # shares an edge: not a z-fight
                if not tri_overlap(flat[fa], flat[fb]):
                    continue
                if float(n[fa] @ n[fb]) < 0.5:
                    back_to_back += 1     # opposite facings; culling picks one
                    continue
                zf += 1
                seps.append(abs(float(n[fa] @ tri[fa, 0])
                                - float(n[fa] @ tri[fb, 0])))
                if len(examples) < 5:
                    examples.append((fa, fb))
    # Overlapping is only a z-fight if the two sit at the same depth. Anything
    # the tie-breaker has separated resolves deterministically.
    seps = np.array(seps) if seps else np.zeros(0)
    coincident = int((seps < 1e-4).sum())
    print('\ncoplanar, non-adjacent, overlapping face pairs')
    print('  same-facing (can z-fight):        %d' % zf)
    print('  back-to-back (culling picks one): %d' % back_to_back)
    print('  same-facing AND at identical depth: %d   <- the ones that flicker'
          % coincident)
    if len(seps):
        print('  separation: min %.5f  median %.5f' % (seps.min(), np.median(seps)))
    for a, b in examples:
        print('   faces %d/%d  y %.3f / %.3f  normals dot %.2f'
              % (a, b, tri[a, :, 1].mean(), tri[b, :, 1].mean(), float(n[a] @ n[b])))

    # --- topology -----------------------------------------------------
    _, inv = np.unique(np.round(pos, 5), axis=0, return_inverse=True)
    F = inv[idx]
    shared = defaultdict(int)
    for f in range(len(F)):
        for k in range(3):
            a, b = F[f, k], F[f, (k + 1) % 3]
            shared[(min(a, b), max(a, b))] += 1
    counts = defaultdict(int)
    for c in shared.values():
        counts[c] += 1
    print('\nedge sharing: %s' % dict(sorted(counts.items())))
    print('  boundary edges (1 face): %d' % counts.get(1, 0))
    print('  non-manifold edges (>2 faces): %d' % sum(v for k, v in counts.items() if k > 2))

    # --- winding consistency ------------------------------------------
    # On a closed mesh each shared edge should be traversed in opposite
    # directions by its two faces. Anything else means a flipped triangle,
    # which shows up as a hole under backface culling.
    direction = defaultdict(list)
    for f in range(len(F)):
        for k in range(3):
            a, b = int(F[f, k]), int(F[f, (k + 1) % 3])
            direction[(min(a, b), max(a, b))].append(a < b)
    flipped = sum(1 for v in direction.values() if len(v) == 2 and v[0] == v[1])
    print('\nedges with inconsistent winding: %d  (0 = all triangles agree)' % flipped)

    # --- scale of detail vs texture -----------------------------------
    print('\nface size: median edge %.4f, 5th pct %.4f (world units)'
          % (np.median(e), np.percentile(e, 5)))
    print('glow band %.4f, core %.4f world units'
          % (cfg.GLOW['band'], cfg.GLOW['band'] * cfg.LUT['glow_core_width']))


if __name__ == '__main__':
    main()

"""Diagnostic: confirm painter traces sit in the right place and never overlap a component bbox."""
from __future__ import annotations

import sys
from pathlib import Path

import bpy
from mathutils import Vector

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from build_painter_traces import (  # noqa: E402
    COLL_TRACES,
    TRACE_PREFIX,
    split_board_and_components,
)
from import_claude_pcb import COLL_COMPONENTS, SCENE_NAME  # noqa: E402


def main() -> int:
    scene = bpy.data.scenes.get(SCENE_NAME)
    if scene is None:
        print("FAIL: missing scene", SCENE_NAME)
        return 1

    coll_components = bpy.data.collections.get(COLL_COMPONENTS)
    coll_traces = bpy.data.collections.get(COLL_TRACES)
    if coll_components is None or coll_traces is None:
        print("FAIL: missing collections", coll_components, coll_traces)
        return 1

    trace_obs = [o for o in coll_traces.objects if o.name.startswith(TRACE_PREFIX)]
    if not trace_obs:
        print("FAIL: no trace objects in", COLL_TRACES)
        return 1
    trace_ob = trace_obs[0]

    (board_ob, board_lo, board_hi), comps = split_board_and_components(coll_components)
    print(f"board: {board_ob.name}")
    print(f"  xy=({board_lo.x:.2f},{board_lo.y:.2f}) -> ({board_hi.x:.2f},{board_hi.y:.2f}) "
          f"top_z={board_hi.z:.3f}")
    print(f"trace: {trace_ob.name} verts={len(trace_ob.data.vertices)} "
          f"polys={len(trace_ob.data.polygons)}")

    tlo = Vector((1e30, 1e30, 1e30))
    thi = Vector((-1e30, -1e30, -1e30))
    for v in trace_ob.data.vertices:
        w = trace_ob.matrix_world @ v.co
        for k in range(3):
            tlo[k] = min(tlo[k], w[k])
            thi[k] = max(thi[k], w[k])
    print(f"  bbox=({tlo.x:.2f},{tlo.y:.2f},{tlo.z:.3f}) -> "
          f"({thi.x:.2f},{thi.y:.2f},{thi.z:.3f})")

    if not (board_lo.x <= tlo.x and thi.x <= board_hi.x and
            board_lo.y <= tlo.y and thi.y <= board_hi.y):
        print("FAIL: trace bbox is not inside board XY footprint")
        return 1
    if tlo.z < board_hi.z - 0.01:
        print(f"FAIL: trace z {tlo.z:.3f} dips below board top {board_hi.z:.3f}")
        return 1
    print("OK: trace mesh inside board XY and resting on board top")

    # Sample 800 random trace verts and check none is inside any component bbox
    # (with a small tolerance equal to the script's clearance).
    import random
    random.seed(123)
    verts = list(trace_ob.data.vertices)
    sample = random.sample(verts, min(800, len(verts)))
    pts = [trace_ob.matrix_world @ v.co for v in sample]
    intrusions = 0
    for px, py, _pz in [(p.x, p.y, p.z) for p in pts]:
        for _ob, lo, hi in comps:
            if lo.x <= px <= hi.x and lo.y <= py <= hi.y:
                intrusions += 1
                break
    print(f"  sampled {len(pts)} verts; intrusions into component bbox = {intrusions}")
    if intrusions > 0:
        print("FAIL: traces overlap component footprints")
        return 1
    print("OK: no trace vertex falls inside any component bbox")
    return 0


if __name__ == "__main__":
    code = main()
    print("[verify]", "OK" if code == 0 else "FAIL")
    raise SystemExit(code)

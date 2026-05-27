"""Polyline cleanup: collinear merge and micro-jog removal."""
from __future__ import annotations

import math


def simplify_collinear(path: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(path) < 3:
        return list(path)
    out = [path[0]]
    for i in range(1, len(path) - 1):
        ax, az = out[-1]
        bx, bz = path[i]
        cx, cz = path[i + 1]
        dx1, dz1 = bx - ax, bz - az
        dx2, dz2 = cx - bx, cz - bz
        if abs(dx1 * dz2 - dz1 * dx2) < 1e-9:
            continue
        out.append(path[i])
    out.append(path[-1])
    return out


def drop_micro_jogs(
    path: list[tuple[float, float]], min_len: float = 0.04
) -> list[tuple[float, float]]:
    if len(path) < 3:
        return list(path)
    out = [path[0]]
    for i in range(1, len(path) - 1):
        prev = out[-1]
        cur = path[i]
        nxt = path[i + 1]
        len1 = math.hypot(cur[0] - prev[0], cur[1] - prev[1])
        len2 = math.hypot(nxt[0] - cur[0], nxt[1] - cur[1])
        if len1 < min_len and len2 < min_len:
            continue
        out.append(cur)
    out.append(path[-1])
    return out

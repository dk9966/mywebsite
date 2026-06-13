#!/usr/bin/env python3
"""Build a circuit-painter / circuit-generator seed from traced circuits + boxes."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACED = ROOT / "plans/circuit design/circuits-traced.json"
OUT = ROOT / "circuit-painter/seeds/circuits-tracing.json"

CELL = 9
SRC_W = 1672
SRC_H = 941
SNAPSHOT_NAME = "Circuits tracing"
HEATSINK_ASPECT = 12 / 9
PAD_CELLS = 6


def cluster(vals, gap=12):
    if not vals:
        return []
    vals = sorted(vals)
    groups = [[vals[0]]]
    for v in vals[1:]:
        if v - groups[-1][-1] <= gap:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [round(sum(g) / len(g)) for g in groups]


def content_bounds(lines, boxes, pad_px):
    xs = [p[0] for line in lines for p in line]
    ys = [p[1] for line in lines for p in line]
    for color in boxes.values():
        for box in color:
            xs.extend([box["x"], box["x"] + box["w"]])
            ys.extend([box["y"], box["y"] + box["h"]])
    return {
        "min_x": min(xs) - pad_px,
        "min_y": min(ys) - pad_px,
        "max_x": max(xs) + pad_px,
        "max_y": max(ys) + pad_px,
    }


def crop_map(bounds):
    min_x = max(0, math.floor(bounds["min_x"] / CELL) * CELL)
    min_y = max(0, math.floor(bounds["min_y"] / CELL) * CELL)
    max_x = min(SRC_W, math.ceil(bounds["max_x"] / CELL) * CELL)
    max_y = min(SRC_H, math.ceil(bounds["max_y"] / CELL) * CELL)
    map_w = max_x - min_x
    map_h = max_y - min_y
    if map_w % CELL:
        map_w += CELL - (map_w % CELL)
        max_x = min_x + map_w
    if map_h % CELL:
        map_h += CELL - (map_h % CELL)
        max_y = min_y + map_h
    return min_x, min_y, map_w, map_h


def px_to_grid(px, py, offset_x, offset_y):
    return (px - offset_x) / CELL, (py - offset_y) / CELL


def horizontal_tracks(box, lines):
    rx, ry, rw, rh = box["x"], box["y"], box["w"], box["h"]
    ys = []
    for line in lines:
        for i in range(len(line) - 1):
            a, b = line[i], line[i + 1]
            ax, ay = a
            bx, by = b
            if abs(ay - by) <= 1:
                y = (ay + by) / 2
                if ry - 18 <= y <= ry + rh + 18:
                    xlo, xhi = min(ax, bx), max(ax, bx)
                    if xhi >= rx and xlo <= rx + rw:
                        ys.append(y - ry)
    return cluster(ys)


def pin_row_error(qfp_y, tracks_px, box_y, offset_y):
    if not tracks_px:
        return 0
    offsets = list(range(0, 14, 2))
    err = 0
    for t in tracks_px:
        target = (box_y - offset_y) / CELL + t / CELL - qfp_y
        err += min(abs(target - off) for off in offsets)
    return err


def place_qfp(box, lines, offset_x, offset_y):
    w_cells = round(box["w"] / CELL)
    h_cells = round(box["h"] / CELL)
    side = max(12, min(18, round(min(box["w"], box["h"]) / CELL)))
    if side % 2:
        side += 1

    gx = round((box["x"] - offset_x) / CELL + (w_cells - side) / 2)
    base_gy = round((box["y"] - offset_y) / CELL + (h_cells - side) / 2)
    h_tracks = horizontal_tracks(box, lines)

    best_gy = base_gy
    best_err = float("inf")
    for gy in range(base_gy - 2, base_gy + 3):
        err = pin_row_error(gy, h_tracks, box["y"], offset_y)
        if err < best_err:
            best_err = err
            best_gy = gy

    return {
        "x": gx,
        "y": best_gy,
        "w": side,
        "h": side,
        "kind": "qfp",
        "qfp": True,
        "rot": 0,
    }


def place_heatsink(box, offset_x, offset_y):
    w_cells = round(box["w"] / CELL)
    h_cells = round(box["h"] / CELL)

    if w_cells / max(h_cells, 1) >= HEATSINK_ASPECT:
        h = max(7, h_cells)
        w = max(10, round(h * HEATSINK_ASPECT))
    else:
        w = max(10, w_cells)
        h = max(7, round(w / HEATSINK_ASPECT))

    gx = round((box["x"] - offset_x) / CELL + (w_cells - w) / 2)
    gy = round((box["y"] - offset_y) / CELL + (h_cells - h) / 2)

    return {
        "x": gx,
        "y": gy,
        "w": w,
        "h": h,
        "kind": "heatsink",
        "qfp": False,
        "rot": 0,
    }


def heatsink_edge_contacts_px(obs, lines, offset_x, offset_y, margin=34):
    """Collect where traces pass near each heatsink edge (distance along edge, px)."""
    ox, oy, ow, oh = obs["x"], obs["y"], obs["w"], obs["h"]
    rx = ox * CELL + offset_x
    ry = oy * CELL + offset_y
    rw, rh = ow * CELL, oh * CELL
    contacts = {side: [] for side in ("top", "right", "bottom", "left")}

    for line in lines:
        for px, py in line:
            if ry - margin <= py <= ry + margin and rx <= px <= rx + rw:
                contacts["top"].append(px - rx)
            if ry + rh - margin <= py <= ry + rh + margin and rx <= px <= rx + rw:
                contacts["bottom"].append(px - rx)
            if rx - margin <= px <= rx + margin and ry <= py <= ry + rh:
                contacts["left"].append(py - ry)
            if rx + rw - margin <= px <= rx + rw + margin and ry <= py <= ry + rh:
                contacts["right"].append(py - ry)
        for i in range(len(line) - 1):
            ax, ay = line[i]
            bx, by = line[i + 1]
            if abs(ay - by) <= 2:
                y = (ay + by) / 2
                x = (ax + bx) / 2
                if abs(y - ry) <= margin and rx - 12 <= x <= rx + rw + 12:
                    contacts["top"].append(x - rx)
                if abs(y - (ry + rh)) <= margin and rx - 12 <= x <= rx + rw + 12:
                    contacts["bottom"].append(x - rx)
            if abs(ax - bx) <= 2:
                x = (ax + bx) / 2
                y = (ay + by) / 2
                if abs(x - rx) <= margin and ry - 12 <= y <= ry + rh + 12:
                    contacts["left"].append(y - ry)
                if abs(x - (rx + rw)) <= margin and ry - 12 <= y <= ry + rh + 12:
                    contacts["right"].append(y - ry)

    return contacts


def contact_clusters(along_px, gap_px=12):
    if not along_px:
        return []
    vals = sorted(along_px)
    groups = [[vals[0]]]
    for v in vals[1:]:
        if v - groups[-1][-1] <= gap_px:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [(sum(g) / len(g), len(g)) for g in groups]


def clusters_to_pin_offsets(clusters, edge_len_cells, min_gap_cells=3, max_pins=2):
    ranked = sorted(clusters, key=lambda item: item[1], reverse=True)
    offsets = []
    for center_px, _ in ranked:
        off = max(0, min(edge_len_cells - 1, round(center_px / CELL)))
        if any(abs(off - kept) < min_gap_cells for kept in offsets):
            continue
        offsets.append(off)
        if len(offsets) >= max_pins:
            break
    return sorted(offsets)


def assign_heatsink_pins(obs, lines, offset_x, offset_y, max_pins=2):
    """Place aux pins only where trace clusters touch the heatsink edge."""
    contacts = heatsink_edge_contacts_px(obs, lines, offset_x, offset_y)
    ranked = []
    for side, vals in contacts.items():
        clusters = contact_clusters(vals)
        if not clusters:
            continue
        edge_len = obs["w"] if side in ("top", "bottom") else obs["h"]
        offsets = clusters_to_pin_offsets(clusters, edge_len, max_pins=max_pins)
        if offsets:
            ranked.append((len(clusters), len(vals), side, offsets))

    if not ranked:
        return None, []

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return ranked[0][2], ranked[0][3]


def simplify_polyline(poly):
    if len(poly) < 2:
        return []
    pts = [poly[0]]
    for i in range(1, len(poly) - 1):
        ax, ay = poly[i - 1]
        bx, by = poly[i]
        cx, cy = poly[i + 1]
        dx1, dy1 = bx - ax, by - ay
        dx2, dy2 = cx - bx, cy - by
        if dx1 == dx2 and dy1 == dy2:
            continue
        pts.append(poly[i])
    if pts[-1] != poly[-1]:
        pts.append(poly[-1])
    return pts


def polyline_length(pts):
    return sum(
        max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        for a, b in zip(pts, pts[1:])
    )


def lines_to_wires(lines, offset_x, offset_y):
    wires = []
    grid_lines = []
    for raw in lines:
        poly = simplify_polyline(raw)
        if len(poly) < 2:
            continue
        grid_pts = [px_to_grid(x, y, offset_x, offset_y) for x, y in poly]
        if polyline_length(grid_pts) < 2:
            continue
        grid_lines.append(grid_pts)
        wires.append(
            {
                "points": [{"x": x, "y": y} for x, y in grid_pts],
                "isBus": False,
                "isGreedy": False,
                "isQFPPin": False,
                "isRoute": False,
                "noPads": True,
                "strokeScale": None,
                "manual": True,
            }
        )
    return wires, grid_lines


def build_snapshot():
    traced = json.loads(TRACED.read_text())
    lines = traced["lines"]
    boxes = traced["boxes"]

    pad_px = PAD_CELLS * CELL
    bounds = content_bounds(lines, boxes, pad_px)
    offset_x, offset_y, map_w, map_h = crop_map(bounds)

    obstacles = []
    for box in boxes["green"]:
        obstacles.append(place_qfp(box, lines, offset_x, offset_y))

    heatsinks = []
    for box in boxes["pink"]:
        heatsinks.append(place_heatsink(box, offset_x, offset_y))

    wires, grid_lines = lines_to_wires(lines, offset_x, offset_y)

    for hs in heatsinks:
        side, offsets = assign_heatsink_pins(hs, lines, offset_x, offset_y)
        if side and offsets:
            hs["auxPinSide"] = side
            hs["auxPinOffsets"] = offsets
        obstacles.append(hs)

    return {
        "id": "circuits_tracing_v2",
        "name": SNAPSHOT_NAME,
        "createdAt": 1781200000000,
        "thumbnail": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        "data": {
            "params": {
                "mapWidth": map_w,
                "mapHeight": map_h,
                "cellSize": CELL,
                "wireLength": 28,
                "cutOffLength": 1,
                "straightness": 15,
                "diagonalChance": 0.5,
                "turnSmoothness": 1,
                "collectiveness": 0,
                "prioritizeLongWires": False,
                "joinEndpoints": False,
                "directionality": 0.8,
                "showGrid": False,
                "showCircuits": True,
                "showGreedyCircuits": False,
                "editWires": True,
                "showBuses": False,
                "qfpStyle": True,
                "qfpPinSpacing": 2,
                "obstaclesEnabled": True,
                "editObstacles": True,
                "pinBusSlantLength": 6,
                "pinBusStraightMax": 14,
                "routeClearanceTarget": 4,
                "routeClearanceBias": 0.75,
                "pinBusRouteMargin": 16,
                "pinBusMaxDetourRatio": 1.75,
                "pinBusCorridorWeight": 0.24,
                "pinBusSpineRatio": 0.52,
                "pinBusWireCount": 4,
                "seed": 1,
                "bgColor": "rgba(51, 5, 51, 1)",
                "fgColor": "rgba(163, 204, 194, 1)",
            },
            "obstacles": obstacles,
            "wires": wires,
        },
    }, offset_x, offset_y, map_w, map_h


def main():
    snap, ox, oy, mw, mh = build_snapshot()
    OUT.write_text(json.dumps(snap, indent=2))
    print(f"Wrote {OUT}")
    print(f"crop offset px: ({ox}, {oy})  map: {mw}x{mh}")
    print(f"obstacles: {len(snap['data']['obstacles'])}")
    print(f"wires: {len(snap['data']['wires'])}")
    for o in snap["data"]["obstacles"]:
        extra = ""
        if o["kind"] == "heatsink":
            extra = f" aux={o.get('auxPinSide')} {o.get('auxPinOffsets')}"
        print(f"  {o['kind']:9} ({o['x']:3},{o['y']:3}) {o['w']}x{o['h']}{extra}")


if __name__ == "__main__":
    main()

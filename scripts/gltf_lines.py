"""Helpers for appending glTF LINES primitives to an existing GLB."""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

GLTF_MAGIC = b"glTF"
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
MODE_LINES = 1


@dataclass(frozen=True)
class LineMeshSpec:
    name: str
    points: np.ndarray  # (n, 3) float32


def read_glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    magic, _version, _length = struct.unpack_from("<4sII", data, 0)
    if magic != GLTF_MAGIC:
        raise ValueError(f"Not a glTF binary: {path}")

    offset = 12
    json_doc: dict | None = None
    bin_blob = b""
    while offset < len(data):
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset : offset + chunk_len]
        offset += chunk_len
        if chunk_type == JSON_CHUNK:
            json_doc = json.loads(chunk)
        elif chunk_type == BIN_CHUNK:
            bin_blob = chunk

    if json_doc is None:
        raise ValueError(f"GLB missing JSON chunk: {path}")
    return json_doc, bin_blob


def write_glb(path: Path, json_doc: dict, bin_blob: bytes) -> None:
    json_bytes = json.dumps(json_doc, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * json_pad

    bin_pad = (4 - (len(bin_blob) % 4)) % 4
    bin_blob = bin_blob + b"\x00" * bin_pad

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_blob)
    header = struct.pack("<4sII", GLTF_MAGIC, 2, total_len)
    json_header = struct.pack("<II", len(json_bytes), JSON_CHUNK)
    bin_header = struct.pack("<II", len(bin_blob), BIN_CHUNK)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + json_header + json_bytes + bin_header + bin_blob)


def _align4(n: int) -> int:
    return (n + 3) & ~3


def _append_accessor(
    doc: dict,
    blob: bytearray,
    array: np.ndarray,
    *,
    target: int | None = None,
    component_type: int,
    type_name: str,
    count: int,
    min_vals: list[float] | None = None,
    max_vals: list[float] | None = None,
) -> int:
    raw = array.tobytes()
    offset = _align4(len(blob))
    if offset > len(blob):
        blob.extend(b"\x00" * (offset - len(blob)))
    blob.extend(raw)
    view_idx = len(doc["bufferViews"])
    view: dict = {
        "buffer": 0,
        "byteOffset": offset,
        "byteLength": len(raw),
    }
    if target is not None:
        view["target"] = target
    doc["bufferViews"].append(view)

    acc_idx = len(doc["accessors"])
    accessor: dict = {
        "bufferView": view_idx,
        "componentType": component_type,
        "count": count,
        "type": type_name,
    }
    if min_vals is not None:
        accessor["min"] = min_vals
    if max_vals is not None:
        accessor["max"] = max_vals
    doc["accessors"].append(accessor)
    return acc_idx


def append_line_meshes(
    doc: dict,
    bin_blob: bytes,
    lines: Iterable[LineMeshSpec],
) -> tuple[dict, bytes]:
    """Append LINES-mode meshes and scene nodes to an existing glTF document."""
    blob = bytearray(bin_blob)
    if "buffers" not in doc:
        doc["buffers"] = [{"byteLength": len(blob)}]
    else:
        doc["buffers"][0]["byteLength"] = len(blob)

    scene_idx = doc.get("scene", 0)
    scene = doc["scenes"][scene_idx]
    if "nodes" not in scene:
        scene["nodes"] = []

    for spec in lines:
        pts = np.asarray(spec.points, dtype=np.float32)
        if pts.ndim != 2 or pts.shape[1] != 3 or len(pts) < 2:
            continue

        pos_acc = _append_accessor(
            doc,
            blob,
            pts,
            target=34962,
            component_type=5126,
            type_name="VEC3",
            count=len(pts),
            min_vals=pts.min(axis=0).tolist(),
            max_vals=pts.max(axis=0).tolist(),
        )

        seg_count = len(pts) - 1
        indices = np.empty(seg_count * 2, dtype=np.uint16)
        for i in range(seg_count):
            indices[i * 2] = i
            indices[i * 2 + 1] = i + 1

        idx_acc = _append_accessor(
            doc,
            blob,
            indices,
            target=34963,
            component_type=5123,
            type_name="SCALAR",
            count=len(indices),
        )

        mesh_idx = len(doc["meshes"])
        doc["meshes"].append(
            {
                "name": spec.name,
                "primitives": [
                    {
                        "attributes": {"POSITION": pos_acc},
                        "indices": idx_acc,
                        "mode": MODE_LINES,
                    }
                ],
            }
        )

        node_idx = len(doc["nodes"])
        doc["nodes"].append({"mesh": mesh_idx, "name": spec.name})
        scene["nodes"].append(node_idx)

    doc["buffers"][0]["byteLength"] = len(blob)
    return doc, bytes(blob)


def merge_line_meshes_into_glb(
    base_glb: Path,
    lines: Iterable[LineMeshSpec],
    out_glb: Path,
) -> int:
    doc, bin_blob = read_glb(base_glb)
    for key in ("accessors", "bufferViews", "meshes", "nodes", "scenes"):
        doc.setdefault(key, [])

    count_before = len(doc["meshes"])
    doc, new_blob = append_line_meshes(doc, bin_blob, lines)
    write_glb(out_glb, doc, new_blob)
    return len(doc["meshes"]) - count_before

// Catalog of PCB-package variants read from public/models/qfp-variants.glb.
//
// The GLB lays out eight rows of packages as crease-edge outlines. Each variant
// contributes a set of `TronLine_..._part_<id>` polylines (e.g. "q4-l-pins").
// We group those polylines per variant, derive a placement footprint and an
// isometric SVG thumbnail, and bucket variants into the eight palette
// categories by their id prefix.

import { useEffect, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { meshOutlineColorForKind } from "./circuit3DMeshes";
import { MESH_LABELS, type MeshKind } from "./circuitMeshBoxes";
import type { CircuitMesh } from "./circuitMeshes";
import {
  DEFAULT_MESH_SIZE,
  meshFootprintSize,
  normalizeMeshRotationYDeg,
} from "./circuitMeshes";
import type { GridPath, Vec3 } from "./gridBuilder";
import { tronPolylinesFromGLB } from "./tronLinesFromGLB";

const CATALOG_URL = "/models/qfp-variants.glb";

/** Palette order for the eight package categories. */
const CATEGORY_ORDER: MeshKind[] = [
  "qfp",
  "soic",
  "cpu",
  "heatsink",
  "io",
  "dimm",
  "pcie",
  "vrm",
];

/** Variant id prefix (letters before the first digit) → palette category. */
const PREFIX_TO_KIND: Record<string, MeshKind> = {
  q: "qfp",
  r: "soic",
  c: "cpu",
  h: "heatsink",
  io: "io",
  d: "dimm",
  p: "pcie",
  v: "vrm",
};

export type VariantThumb = { d: string; viewBox: string };

export type VariantEntry = {
  /** Stable catalog id, e.g. "q4-l-pins". */
  id: string;
  /** Display label, e.g. "QFP 4". */
  label: string;
  kind: MeshKind;
  /** 0-based position within its category. */
  index: number;
  /** Outline polylines centered on XZ with the base at Y = 0, authored scale. */
  polylines: Vec3[][];
  /** Authored bounding size. */
  natural: { w: number; d: number; h: number };
  /** Footprint applied when placing (uniform-scaled to the category default). */
  placeSize: { w: number; h: number };
  thumb: VariantThumb;
};

export type VariantCategory = {
  kind: MeshKind;
  label: string;
  color: string;
  variants: VariantEntry[];
};

export type VariantCatalog = {
  categories: VariantCategory[];
  byId: Map<string, VariantEntry>;
};

const round = (n: number): number => Math.round(n * 1000) / 1000;

const COS30 = Math.cos(Math.PI / 6);

/** Isometric projection of the centered polylines into a compact SVG path. */
function buildThumb(polylines: Vec3[][]): VariantThumb {
  const project = ([x, y, z]: Vec3): [number, number] => [
    (x - z) * COS30,
    -((x + z) * 0.5 - y), // world-up y → SVG y-down
  ];

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  const screen = polylines.map((poly) =>
    poly.map((p) => {
      const [sx, sy] = project(p);
      if (sx < minX) minX = sx;
      if (sx > maxX) maxX = sx;
      if (sy < minY) minY = sy;
      if (sy > maxY) maxY = sy;
      return [sx, sy] as [number, number];
    }),
  );

  if (!Number.isFinite(minX)) return { d: "", viewBox: "0 0 1 1" };

  const flipCx = (minX + maxX) / 2;
  const flipCy = (minY + maxY) / 2;

  const pad = Math.max(maxX - minX, maxY - minY) * 0.06 + 0.02;
  const parts: string[] = [];
  for (const poly of screen) {
    if (poly.length < 2) continue;
    const [x0, y0] = poly[0];
    let d = `M${round(2 * flipCx - x0)} ${round(2 * flipCy - y0)}`;
    for (let i = 1; i < poly.length; i++) {
      d += `L${round(2 * flipCx - poly[i][0])} ${round(2 * flipCy - poly[i][1])}`;
    }
    parts.push(d);
  }

  return {
    d: parts.join(" "),
    viewBox: `${round(minX - pad)} ${round(minY - pad)} ${round(
      maxX - minX + 2 * pad,
    )} ${round(maxY - minY + 2 * pad)}`,
  };
}

function buildEntry(id: string, kind: MeshKind, raw: Vec3[][]): VariantEntry {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;
  for (const poly of raw) {
    for (const [x, y, z] of poly) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
      if (z < minZ) minZ = z;
      if (z > maxZ) maxZ = z;
    }
  }

  const cx = (minX + maxX) / 2;
  const cz = (minZ + maxZ) / 2;
  const polylines = raw.map((poly) =>
    poly.map(([x, y, z]) => [x - cx, y - minY, z - cz] as Vec3),
  );

  const natural = {
    w: Math.max(maxX - minX, 1e-4),
    d: Math.max(maxZ - minZ, 1e-4),
    h: Math.max(maxY - minY, 1e-4),
  };
  const target = Math.max(DEFAULT_MESH_SIZE[kind].w, DEFAULT_MESH_SIZE[kind].h);
  const scale = target / Math.max(natural.w, natural.d);

  return {
    id,
    label: id,
    kind,
    index: 0,
    polylines,
    natural,
    placeSize: { w: natural.w * scale, h: natural.d * scale },
    thumb: buildThumb(polylines),
  };
}

function categoryOfId(id: string): { kind: MeshKind; num: number } | null {
  const m = /^([a-z]+)(\d+)/.exec(id);
  if (!m) return null;
  const kind = PREFIX_TO_KIND[m[1]];
  if (!kind) return null;
  return { kind, num: Number.parseInt(m[2], 10) };
}

/** Build the palette catalog from a loaded qfp-variants.glb scene. */
export function buildCatalogFromScene(scene: THREE.Object3D): VariantCatalog {
  const groups = new Map<string, Vec3[][]>();
  for (const poly of tronPolylinesFromGLB(scene)) {
    const i = poly.name.indexOf("_part_");
    if (i < 0) continue;
    const id = poly.name.slice(i + "_part_".length);
    const list = groups.get(id);
    if (list) list.push(poly.waypoints);
    else groups.set(id, [poly.waypoints]);
  }

  const buckets = new Map<MeshKind, { num: number; entry: VariantEntry }[]>();
  for (const [id, polylines] of groups) {
    const cat = categoryOfId(id);
    if (!cat) continue;
    const arr = buckets.get(cat.kind) ?? [];
    arr.push({ num: cat.num, entry: buildEntry(id, cat.kind, polylines) });
    buckets.set(cat.kind, arr);
  }

  const categories: VariantCategory[] = [];
  const byId = new Map<string, VariantEntry>();
  for (const kind of CATEGORY_ORDER) {
    const arr = (buckets.get(kind) ?? []).sort((a, b) => a.num - b.num);
    if (arr.length === 0) continue;
    const variants = arr.map(({ entry }, i) => {
      const withMeta: VariantEntry = {
        ...entry,
        index: i,
        label: `${MESH_LABELS[kind]} ${i + 1}`,
      };
      byId.set(withMeta.id, withMeta);
      return withMeta;
    });
    categories.push({
      kind,
      label: MESH_LABELS[kind],
      color: meshOutlineColorForKind(kind),
      variants,
    });
  }

  return { categories, byId };
}

let catalogPromise: Promise<VariantCatalog> | null = null;

export function loadVariantCatalog(): Promise<VariantCatalog> {
  if (!catalogPromise) {
    catalogPromise = new GLTFLoader()
      .loadAsync(CATALOG_URL)
      .then((gltf) => buildCatalogFromScene(gltf.scene));
  }
  return catalogPromise;
}

/** Resolves the shared variant catalog once and returns it (null until ready). */
export function useVariantCatalog(): VariantCatalog | null {
  const [catalog, setCatalog] = useState<VariantCatalog | null>(null);
  useEffect(() => {
    let alive = true;
    loadVariantCatalog()
      .then((c) => {
        if (alive) setCatalog(c);
      })
      .catch((err) => console.error("[qfpVariantCatalog] load failed", err));
    return () => {
      alive = false;
    };
  }, []);
  return catalog;
}

/**
 * Real outline geometry for meshes placed from the variant palette. Each
 * variant's centered polylines are scaled to the un-rotated footprint, yawed
 * by `rotationYDeg`, then lifted to the board plane.
 *
 * `colorMode: "kind"` (default) tints by mesh kind; `"global"` omits
 * per-path color so the renderer uses lineConfig.
 */
export function variantOutlinePaths(
  meshes: CircuitMesh[],
  catalog: VariantCatalog,
  boardY: number,
  colorMode: "kind" | "global" = "kind",
): GridPath[] {
  const out: GridPath[] = [];
  for (const m of meshes) {
    if (!m.variant) continue;
    const v = catalog.byId.get(m.variant);
    if (!v) continue;

    const lineColor =
      colorMode === "kind" ? meshOutlineColorForKind(m.kind) : undefined;
    const { w: fw, h: fd } = meshFootprintSize(m);
    const sx = fw / v.natural.w;
    const sz = fd / v.natural.d;
    const sy = Math.sqrt(Math.max(sx * sz, 1e-9));
    const cx = (m.minX + m.maxX) / 2;
    const cz = (m.minZ + m.maxZ) / 2;
    const rad =
      (normalizeMeshRotationYDeg(m.rotationYDeg ?? 0) * Math.PI) / 180;
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);

    v.polylines.forEach((poly, i) => {
      out.push({
        id: `${m.id}-v-${i}`,
        spawnTime: 0,
        ...(lineColor ? { lineColor } : {}),
        waypoints: poly.map(([x, y, z]) => {
          const lx = x * sx;
          const lz = z * sz;
          return [
            cx + lx * cos + lz * sin,
            boardY + y * sy,
            cz - lx * sin + lz * cos,
          ] as Vec3;
        }),
      });
    });
  }
  return out;
}

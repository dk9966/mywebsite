import { MESH_LABELS, MESH_PALETTE, type MeshKind } from "./circuitMeshBoxes";
import { DEFAULT_MESH_SIZE } from "./circuitMeshes";

export type MeshVariation = {
  id: string;
  label: string;
  size: MeshSize;
};

export type MeshTypeGroup = {
  kind: MeshKind;
  label: string;
  variations: MeshVariation[];
};

function sz(w: number, h: number): MeshSize {
  return { w, h };
}

function scaled(kind: MeshKind, wMul: number, hMul: number): MeshSize {
  const base = DEFAULT_MESH_SIZE[kind];
  return { w: base.w * wMul, h: base.h * hMul };
}

const VARIATIONS_BY_KIND: Record<MeshKind, Omit<MeshVariation, "id">[]> = {
  qfp: [
    { label: "QFP-32", size: scaled("qfp", 0.85, 0.85) },
    { label: "QFP-48", size: sz(3.5, 3.5) },
    { label: "QFP-64", size: scaled("qfp", 1.15, 1.15) },
    { label: "LQFP wide", size: scaled("qfp", 1.25, 1.0) },
    { label: "Ceramic", size: scaled("qfp", 1.0, 1.0) },
  ],
  soic: [
    { label: "SOIC-8", size: scaled("soic", 0.75, 0.85) },
    { label: "SOIC-16", size: sz(4, 2) },
    { label: "SOIC-20", size: scaled("soic", 1.2, 1.0) },
    { label: "Wide body", size: scaled("soic", 1.0, 1.25) },
    { label: "Narrow", size: scaled("soic", 0.9, 0.75) },
  ],
  capacitor: [
    { label: "Electrolytic", size: sz(2, 2) },
    { label: "Tantalum", size: scaled("capacitor", 0.85, 1.1) },
    { label: "Film", size: scaled("capacitor", 1.2, 0.9) },
    { label: "Stacked", size: scaled("capacitor", 0.9, 1.35) },
    { label: "Squat SMD", size: scaled("capacitor", 1.1, 0.75) },
  ],
  heatsink: [
    { label: "Finned", size: sz(4.5, 2.5) },
    { label: "Pin-fin", size: scaled("heatsink", 1.0, 1.1) },
    { label: "Crosshatch", size: scaled("heatsink", 0.95, 0.95) },
    { label: "Stepped", size: scaled("heatsink", 0.9, 1.0) },
    { label: "Compact", size: scaled("heatsink", 0.75, 0.7) },
  ],
  drum: [
    { label: "Oct 6", size: scaled("drum", 0.85, 0.85) },
    { label: "Oct 8", size: sz(3, 3) },
    { label: "Oct 10", size: scaled("drum", 1.15, 1.15) },
    { label: "Vented", size: scaled("drum", 1.0, 1.0) },
    { label: "Tall", size: scaled("drum", 0.95, 1.25) },
  ],
  header: [
    { label: "1×10", size: scaled("header", 0.9, 1.0) },
    { label: "2×10", size: scaled("header", 1.0, 1.35) },
    { label: "Shrouded", size: scaled("header", 1.05, 1.1) },
    { label: "Right angle", size: scaled("header", 1.0, 1.2) },
    { label: "Terminal", size: scaled("header", 1.15, 1.4) },
  ],
  connector: [
    { label: "Port", size: sz(4, 1.8) },
    { label: "Keyed", size: scaled("connector", 1.05, 1.05) },
    { label: "USB", size: scaled("connector", 0.95, 1.15) },
    { label: "RJ45", size: scaled("connector", 1.0, 1.25) },
    { label: "SD slot", size: scaled("connector", 0.9, 0.85) },
  ],
  smd: [
    { label: "Resistor", size: scaled("smd", 0.9, 0.9) },
    { label: "LED", size: scaled("smd", 1.0, 1.0) },
    { label: "Inductor", size: scaled("smd", 1.0, 1.25) },
    { label: "Crystal", size: scaled("smd", 1.1, 1.15) },
    { label: "4-pad", size: scaled("smd", 1.15, 1.0) },
  ],
  pad: [
    { label: "Small", size: scaled("pad", 0.85, 0.85) },
    { label: "Standard", size: sz(1.2, 1.2) },
    { label: "Large", size: scaled("pad", 1.35, 1.35) },
  ],
  via: [
    { label: "Small", size: scaled("via", 0.85, 0.85) },
    { label: "Standard", size: sz(1, 1) },
    { label: "Large", size: scaled("via", 1.35, 1.35) },
  ],
};

export const MESH_TYPE_GROUPS: MeshTypeGroup[] = MESH_PALETTE.map((kind) => ({
  kind,
  label: MESH_LABELS[kind],
  variations: VARIATIONS_BY_KIND[kind].map((v, i) => ({
    ...v,
    id: `${kind}-${i}`,
  })),
}));

export function meshVariationById(
  kind: MeshKind,
  variationId: string,
): MeshVariation | undefined {
  return MESH_TYPE_GROUPS.find((g) => g.kind === kind)?.variations.find(
    (v) => v.id === variationId,
  );
}

export function defaultMeshSize(kind: MeshKind): MeshSize {
  return DEFAULT_MESH_SIZE[kind];
}

// Component meshes for the 2D circuits editor: plain boxes with a centered
// type label (matching circuit-painter palette names). No pin tabs — the box
// edge is the connection boundary and traces meet it directly.

/** Mesh kinds aligned with circuit-painter/js/components.js palette ids. */
export type MeshKind =
  | "qfp"
  | "soic"
  | "capacitor"
  | "heatsink"
  | "drum"
  | "header"
  | "connector"
  | "smd"
  | "pad"
  | "via";

/** Palette order for the editor mesh menu (matches circuit-painter). */
export const MESH_PALETTE: MeshKind[] = [
  "qfp",
  "soic",
  "capacitor",
  "heatsink",
  "drum",
  "header",
  "connector",
  "smd",
  "pad",
  "via",
];

export const MESH_LABELS: Record<MeshKind, string> = {
  qfp: "QFP",
  soic: "SOIC",
  capacitor: "Cap",
  heatsink: "Heatsink",
  drum: "Drum",
  header: "Header",
  connector: "Connector",
  smd: "SMD",
  pad: "Pad",
  via: "Via",
};

export type MeshStyle = { fg: string; bg: string };

export type ScreenBox = { x: number; y: number; w: number; h: number };

/** Hollow box filled with bg, stroked at the footprint edge, label centered. */
export function drawMeshBox(
  ctx: CanvasRenderingContext2D,
  box: ScreenBox,
  kind: MeshKind,
  style: MeshStyle,
): void {
  const { x, y, w, h } = box;
  if (w < 2 || h < 2) return;

  ctx.fillStyle = style.bg;
  ctx.fillRect(x, y, w, h);

  const sw = Math.max(1, Math.min(w, h) * 0.07);
  ctx.strokeStyle = style.fg;
  ctx.lineWidth = sw;
  ctx.strokeRect(x + sw / 2, y + sw / 2, w - sw, h - sw);

  const label = MESH_LABELS[kind];
  const fontSize = Math.max(7, Math.min(w, h) * 0.26);
  ctx.fillStyle = style.fg;
  ctx.font = `${fontSize}px ui-monospace, SFMono-Regular, Menlo, monospace`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, x + w / 2, y + h / 2);
}

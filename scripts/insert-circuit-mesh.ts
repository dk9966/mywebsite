/**
 * Insert a palette mesh into a circuit tuning JSON (for agents / automation).
 *
 *   pnpm run insert-circuit-mesh -- --variant "QFP 3" --at 12,6
 *   pnpm run insert-circuit-mesh -- --variant q3-plain-prism --at 12,6 --version 2
 *   pnpm run insert-circuit-mesh -- --variant "QFP 3" --at 12,6 --dry-run
 *
 * Resolves labels via src/data/mesh-variant-catalog.json (regenerate with
 * pnpm run export-mesh-variant-catalog if the GLB changed).
 */
import { readFileSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import {
  bboxFromCenter,
  formatVariantSummary,
  resolveVariantRef,
  type MeshVariantManifest,
} from "../src/lib/meshVariantManifest";
import {
  nextMeshUserIdFromEdits,
  type CircuitMesh,
  type CircuitMeshEdits,
} from "../src/lib/circuitMeshes";
import type { CircuitTuning } from "../src/stores/circuitTuning";

const MANIFEST_DEFAULT = fileURLToPath(
  new URL("../src/data/mesh-variant-catalog.json", import.meta.url),
);
const TUNING_DEFAULT = fileURLToPath(
  new URL("../src/data/circuits-tuning.json", import.meta.url),
);

type Args = {
  variant: string;
  cx: number;
  cz: number;
  inPath: string;
  manifestPath: string;
  dryRun: boolean;
  label: string;
};

function parseAt(raw: string): { cx: number; cz: number } {
  const parts = raw.split(",").map((s) => s.trim());
  if (parts.length !== 2) {
    throw new Error(`--at expects cx,cz (got "${raw}")`);
  }
  const cx = Number.parseFloat(parts[0]);
  const cz = Number.parseFloat(parts[1]);
  if (!Number.isFinite(cx) || !Number.isFinite(cz)) {
    throw new Error(`--at expects numeric cx,cz (got "${raw}")`);
  }
  return { cx, cz };
}

function parseArgs(argv: string[]): Args {
  let variant = "";
  let at = "";
  let inPath = TUNING_DEFAULT;
  let manifestPath = MANIFEST_DEFAULT;
  let dryRun = false;
  let label = "circuits-tuning.json";

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--variant") variant = argv[++i];
    else if (arg === "--at") at = argv[++i];
    else if (arg === "--version") {
      const name = argv[++i];
      inPath = fileURLToPath(
        new URL(`../src/data/circuit-versions/${name}.json`, import.meta.url),
      );
      label = `version ${name}`;
    } else if (arg === "--in") {
      inPath = argv[++i];
      label = inPath;
    } else if (arg === "--manifest") manifestPath = argv[++i];
    else if (arg === "--dry-run") dryRun = true;
    else if (arg === "--help" || arg === "-h") {
      console.log(`Usage:
  pnpm run insert-circuit-mesh -- --variant "QFP 3" --at cx,cz [--version N] [--dry-run]

Options:
  --variant   Palette label (QFP 3) or variant id (q3-plain-prism)
  --at        Center position on the board plane: cx,cz
  --version   Edit src/data/circuit-versions/N.json instead of circuits-tuning.json
  --in        Explicit tuning JSON path
  --manifest  Path to mesh-variant-catalog.json
  --dry-run   Print the entry without writing
`);
      process.exit(0);
    }
  }

  if (!variant) throw new Error("Missing --variant");
  if (!at) throw new Error("Missing --at");

  return { variant, ...parseAt(at), inPath, manifestPath, dryRun, label };
}

function loadManifest(path: string): MeshVariantManifest {
  return JSON.parse(readFileSync(path, "utf8")) as MeshVariantManifest;
}

function loadTuning(path: string): CircuitTuning {
  const raw = JSON.parse(readFileSync(path, "utf8")) as Partial<CircuitTuning>;
  return {
    ...raw,
    topology: raw.topology ?? { geometry: {}, deleted: [], added: [] },
    meshEdits: raw.meshEdits ?? { geometry: {}, deleted: [], added: [] },
  } as CircuitTuning;
}

function bboxesOverlap(
  a: Pick<CircuitMesh, "minX" | "maxX" | "minZ" | "maxZ">,
  b: Pick<CircuitMesh, "minX" | "maxX" | "minZ" | "maxZ">,
): boolean {
  return (
    a.minX < b.maxX &&
    a.maxX > b.minX &&
    a.minZ < b.maxZ &&
    a.maxZ > b.minZ
  );
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const manifest = loadManifest(args.manifestPath);
  const variant = resolveVariantRef(manifest, args.variant);
  const tuning = loadTuning(args.inPath);
  const edits: CircuitMeshEdits = tuning.meshEdits ?? {
    geometry: {},
    deleted: [],
    added: [],
  };

  const id = nextMeshUserIdFromEdits(edits);
  const bbox = bboxFromCenter(args.cx, args.cz, variant.placeSize);
  const mesh: CircuitMesh = {
    id,
    kind: variant.kind,
    ...bbox,
    variant: variant.id,
  };

  const overlaps = (edits.added ?? []).filter((m) => bboxesOverlap(mesh, m));
  if (overlaps.length > 0) {
    console.warn(
      `Warning: new mesh overlaps ${overlaps.length} existing added mesh(es): ${overlaps.map((m) => m.id).join(", ")}`,
    );
    console.warn(
      "  Run export-board-spatial and pick a corridor center, or adjust --at.",
    );
  }

  console.log(`Insert into ${args.label}:`);
  console.log(`  ${formatVariantSummary(variant)}`);
  console.log(`  center=(${args.cx}, ${args.cz}) id=${id}`);
  console.log(
    `  bbox minX=${bbox.minX} maxX=${bbox.maxX} minZ=${bbox.minZ} maxZ=${bbox.maxZ}`,
  );

  if (args.dryRun) {
    console.log("\nDry run — meshEdits.added entry:");
    console.log(JSON.stringify(mesh, null, 2));
    return;
  }

  const nextEdits: CircuitMeshEdits = {
    ...edits,
    added: [...(edits.added ?? []), mesh],
  };
  const nextTuning = { ...tuning, meshEdits: nextEdits };
  writeFileSync(args.inPath, `${JSON.stringify(nextTuning, null, 2)}\n`, "utf8");

  console.log(`\nWrote ${args.inPath}`);
  console.log("Next: pnpm run export-board-spatial [-- --version N]");
}

main();

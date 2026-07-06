/**
 * Export an agent-readable mesh variant catalog from qfp-variants.glb.
 *
 *   pnpm run export-mesh-variant-catalog
 *   pnpm tsx scripts/export-mesh-variant-catalog.ts --out path.json
 *
 * Default output: src/data/mesh-variant-catalog.json
 */
import { readFileSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { serializeVariantCatalogForAgent } from "../src/lib/meshVariantManifest";
import { buildCatalogFromScene } from "../src/lib/qfpVariantCatalog";

const GLB = fileURLToPath(
  new URL("../public/models/qfp-variants.glb", import.meta.url),
);
const OUT_DEFAULT = fileURLToPath(
  new URL("../src/data/mesh-variant-catalog.json", import.meta.url),
);

function parseArgs(argv: string[]): { outPath: string } {
  let outPath = OUT_DEFAULT;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--out") outPath = argv[++i];
  }
  return { outPath };
}

function loadScene(): Promise<THREE.Object3D> {
  const buf = readFileSync(GLB);
  const arr = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const loader = new GLTFLoader();
  return new Promise((resolve, reject) => {
    loader.parse(arr as ArrayBuffer, "", (g) => resolve(g.scene), reject);
  });
}

async function main() {
  const { outPath } = parseArgs(process.argv.slice(2));
  const scene = await loadScene();
  const catalog = buildCatalogFromScene(scene);
  const manifest = serializeVariantCatalogForAgent(catalog, {
    generatedAt: new Date().toISOString(),
    sourceGlb: "public/models/qfp-variants.glb",
  });

  writeFileSync(outPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

  console.log(`Mesh variant catalog written to ${outPath}`);
  console.log(
    `  categories=${manifest.categories.length} variants=${manifest.variants.length}`,
  );
  for (const cat of manifest.categories) {
    console.log(`  ${cat.label}: ${cat.variantIds.length} variants`);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

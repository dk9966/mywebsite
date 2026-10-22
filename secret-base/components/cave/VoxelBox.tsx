import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import * as VOXELIZE from "@voxelize/core";
import type { CaveManifest } from "./caveAssets";
import { blockTexture, BLOCK_TEXTURES } from "./voxelTextures";
import { CAVE_FLAGS } from "./caveFlags";

/** Must match voxel-server/src/main.rs. */
const BOX = { width: 28, height: 22, depth: 18, x0: 1, y0: 1, z0: 0 };
/** Metres per block: the 14 m × 11 m box face covers the 9.8 m × 8 m hole. */
const BLOCK = 0.5;
/** Interior floor sits this far below the lowest point of the rim. */
const FLOOR_DROP = 1.5;
/**
 * Voxelize's torch light is a fixed curve, so the box is brought down to the
 * cave's exposure through its albedo (applied in linear light). Matched against
 * the baked rock around the hole.
 */
const VOXEL_EXPOSURE = 0.2;
/** Lantern blocks: still the brightest thing in the room, but not glaring. */
const VOXEL_GLOW = 0.25;
/**
 * The canvas renders on demand: after any server message, keep drawing this
 * long so chunk meshes built in Voxelize's workers make it to the screen.
 */
const SETTLE_MS = 1500;
/** While chunk work is pending but not moving, look again on a backoff instead. */
const POLL_MIN_MS = 250;
const POLL_MAX_MS = 4000;
/**
 * Messages that change what the box looks like. The server also streams
 * physics impulses and clock stats for as long as the client syncs, which
 * would otherwise keep waking the render loop forever.
 */
const VISIBLE_MESSAGES = new Set(["INIT", "LOAD", "UNLOAD", "UPDATE"]);
const SERVER = CAVE_FLAGS.voxelServer ?? import.meta.env.VITE_VOXEL_SERVER ?? "http://localhost:4100";
const WORLD_NAME = "cave-box";

/**
 * Places the voxel grid in the rear hole. Voxel +Z runs into the rock, +Y up,
 * and +X = up × into, which faces the camera's left.
 */
function holeTransform(hole: CaveManifest["hole"]) {
  const up = new THREE.Vector3(...hole.up);
  const into = new THREE.Vector3(...hole.into);
  const x = new THREE.Vector3().crossVectors(up, into).normalize();
  const basis = new THREE.Matrix4().makeBasis(x, up, into);
  const quaternion = new THREE.Quaternion().setFromRotationMatrix(basis);
  // Grid point (x0 + width/2, y0, z0) lands on the hole centre, FLOOR_DROP down.
  const origin = new THREE.Vector3(...hole.origin)
    .addScaledVector(up, -FLOOR_DROP)
    .addScaledVector(x, -(BOX.x0 + BOX.width / 2) * BLOCK)
    .addScaledVector(up, -BOX.y0 * BLOCK)
    .addScaledVector(into, -BOX.z0 * BLOCK);
  return { position: origin, quaternion };
}

/**
 * The Voxelize world recessed into the hole behind the central platform.
 * Terrain, lighting and edits come from the Rust server in `voxel-server/`
 * (`npm run voxel-server`); without it the hole simply stays dark.
 */
export function VoxelBox({ hole }: { hole: CaveManifest["hole"] }) {
  const camera = useThree((s) => s.camera);
  const invalidate = useThree((s) => s.invalidate);
  const awakeUntil = useRef(0);
  const pipelineState = useRef("");
  const poll = useRef({ timer: 0, delay: POLL_MIN_MS });
  const group = useRef<THREE.Group>(null);
  const live = useRef<{ world: VOXELIZE.World; network: VOXELIZE.Network; ready: boolean } | null>(null);
  const begin = useRef<(() => void) | null>(null);
  const placement = useMemo(() => holeTransform(hole), [hole]);
  const center = useMemo(
    () => new THREE.Vector3(BOX.x0 + BOX.width / 2, BOX.y0 + BOX.height / 2, BOX.z0 + BOX.depth / 2),
    [],
  );

  useEffect(() => {
    const parent = group.current;
    if (!parent) return;
    const world = new VOXELIZE.World({
      textureUnitDimension: 16,
      defaultRenderRadius: 4,
      isCullingChunksByFrustum: false,
      isCullingChunksByOcclusion: false,
      // The box is lit only by its own lamps; a little ambient keeps the
      // unlit corners from crushing harder than the surrounding rock.
      minLightLevel: 0.3,
    });
    world.sky.visible = false;
    world.clouds.visible = false;
    // Voxelize freezes the World's matrix (matrixAutoUpdate = false) and its
    // chunk groups only inherit it when they are (re)built, so the hole
    // placement goes on the World itself, applied once before any chunk loads.
    world.position.copy(placement.position);
    world.quaternion.copy(placement.quaternion);
    world.scale.setScalar(BLOCK);
    world.updateMatrix();
    const network = new VOXELIZE.Network();
    const wake = () => {
      awakeUntil.current = performance.now() + SETTLE_MS;
      invalidate();
    };
    network.register(world, { onMessage: (message) => VISIBLE_MESSAGES.has(String(message.type)) && wake() });
    parent.add(world);
    world.updateMatrixWorld(true);
    const state = { world, network, ready: false };
    const pollState = poll.current;
    live.current = state;
    let stopped = false;

    // Voxelize's handshake spins up a dozen decode, mesh and light workers.
    // Started with the box it held the socket's open event behind the cave's
    // first-frame GPU work for ~15 s and slowed that work too; it starts once
    // the cave is on screen instead (see useFrame).
    begin.current = () => (async () => {
      await network.connect(SERVER, { secret: "secret-base" });
      if (stopped) return;
      await network.join(WORLD_NAME);
      if (stopped) return;
      await world.initialize();
      for (const [name, faces] of Object.entries(BLOCK_TEXTURES)) {
        const block = world.getBlockByName(name);
        if (!block) continue;
        for (const [faceGroup, texture] of Object.entries(faces)) {
          const names = block.faces
            .map((f: { name: string }) => f.name)
            .filter((n: string) => faceGroup === "all" || faceGroup.split(",").includes(n));
          if (names.length) world.applyBlockTexture(name, names, blockTexture(texture, VOXEL_EXPOSURE, VOXEL_GLOW));
        }
      }
      // Cave-matched voxel lighting: cool, dim, no sun.
      const u = world.chunkRenderer.uniforms;
      u.sunlightIntensity.value = 0;
      // Depth haze in the cave's blue, so the room recedes into the rock
      // rather than sitting on top of it (distances in scene metres).
      u.fogColor.value.setRGB(0.028, 0.05, 0.072, THREE.LinearSRGBColorSpace);
      u.fogNear.value = 28;
      u.fogFar.value = 75;
      state.ready = true;
      wake();
    })().catch((error) => {
      if (!stopped) console.warn("[voxels] Voxelize server unavailable — run `npm run voxel-server`.", error);
    });

    return () => {
      begin.current = null;
      stopped = true;
      live.current = null;
      window.clearTimeout(pollState.timer);
      pollState.timer = 0;
      network.disconnect();
      parent.remove(world);
    };
  }, [placement, invalidate]);

  useFrame(() => {
    if (begin.current) {
      // First frame: let it finish drawing, then connect.
      window.setTimeout(begin.current, 0);
      begin.current = null;
    }
    const state = live.current;
    if (!state?.ready || !group.current) return;
    const local = state.world.worldToLocal(camera.position.clone());
    state.world.update(center, local.sub(center).normalize().negate(), camera);
    // The World never updates its own subtree (matrixAutoUpdate is off), and
    // its chunk BatchedMesh is added later; push the hole placement down.
    state.world.updateMatrixWorld(true);
    state.network.sync();
    state.network.flush();
    // Chunks are requested and meshed a few per update: draw at full rate while
    // the pipelines make progress, then poll on a backoff while work is still
    // pending (a stalled job must not pin the GPU), and stop once idle.
    const { chunkPipeline, meshPipeline } = state.world;
    const pipeline = [
      chunkPipeline.requestedCount,
      chunkPipeline.processingCount,
      chunkPipeline.loadedCount,
      meshPipeline.dirtyCount,
      meshPipeline.inFlightJobCount(),
    ];
    const signature = pipeline.join();
    if (signature !== pipelineState.current) {
      pipelineState.current = signature;
      awakeUntil.current = performance.now() + SETTLE_MS;
      poll.current.delay = POLL_MIN_MS;
    }
    if (performance.now() < awakeUntil.current) {
      invalidate();
    } else if (pipeline[0] + pipeline[1] + pipeline[3] + pipeline[4] > 0 && !poll.current.timer) {
      poll.current.timer = window.setTimeout(() => {
        poll.current.timer = 0;
        invalidate();
      }, poll.current.delay);
      poll.current.delay = Math.min(poll.current.delay * 2, POLL_MAX_MS);
    }
  });

  return (
    <group ref={group} name="voxelBox" />
  );
}

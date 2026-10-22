import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { EffectComposer, EffectPass, RenderPass, SMAAEffect } from "postprocessing";
import { BlenderLens } from "../scene/CameraRig";
import { BlenderControls, type BlenderView } from "./BlenderControls";
import { loadCaveAssets, linear, type CaveAssets } from "./caveAssets";
import { applyCaveMaterials } from "./caveMaterials";
import { attachShadows, renderSurfaceShadows, TEXELS_PER_LIGHT, type PackedLights } from "./caveLighting";
import { LightStartup } from "./caveStartup";
import { bootSkipped } from "../../../src/lib/bootSequence";
import { amberBloom, HazeEffect, LogEncodeEffect, PixelFilterEffect, renderSpotShadows, ViewLutEffect } from "./caveEffects";
import { VoxelBox } from "./VoxelBox";
import { CaveLabels } from "./CaveLabels";
import { CavePanels } from "./CavePanels";
import { BeamEffect } from "./caveBeams";
import { CAVE_FLAGS, CAVE_TUNING } from "./caveFlags";
import { ZoomDirector, type Tuning } from "./caveZoom";
import zoomLayoutFile from "./zoomLayout.json";
import "./cave.css";

const ORBIT_DISTANCE = 21;
const zoomLayout = zoomLayoutFile as Record<string, Tuning>;

function CameraFromBlender({ assets }: { assets: CaveAssets }) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const { position, direction, up } = assets.manifest.camera;
  useLayoutEffect(() => {
    camera.position.set(...position);
    camera.up.set(...up);
    camera.lookAt(
      position[0] + direction[0] * ORBIT_DISTANCE,
      position[1] + direction[1] * ORBIT_DISTANCE,
      position[2] + direction[2] * ORBIT_DISTANCE,
    );
    camera.updateProjectionMatrix();
  }, [camera, position, direction, up]);
  return <BlenderLens lens={assets.manifest.camera.lens} sensor={assets.manifest.camera.sensor} />;
}

/**
 * The camera's shot (the Blender camera, or a platform zoom's) applied to the
 * camera and to drei's `<Html transform>` layers; see caveZoom.ts.
 */
function CameraView({ zoom }: { zoom: ZoomDirector }) {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const size = useThree((s) => s.size);
  useLayoutEffect(() => {
    zoom.setSize(size.width, size.height);
  }, [zoom, size]);
  useLayoutEffect(() => () => camera.clearViewOffset(), [camera]);
  useEffect(() => zoom.attach(), [zoom]);
  useEffect(() => () => zoom.dispose(), [zoom]);
  // Before drei's Html layers (priority 0) read the camera.
  useFrame(() => zoom.beforeFrame(), -1);
  return null;
}

/** Blender-style viewport navigation, starting from the scene camera. */
function CaveControls({ assets }: { assets: CaveAssets }) {
  const { position, direction } = assets.manifest.camera;
  const view = useMemo<BlenderView>(
    () => ({
      position,
      target: [
        position[0] + direction[0] * ORBIT_DISTANCE,
        position[1] + direction[1] * ORBIT_DISTANCE,
        position[2] + direction[2] * ORBIT_DISTANCE,
      ],
    }),
    [position, direction],
  );
  if (CAVE_FLAGS.locked) return null;
  return <BlenderControls view={view} />;
}

function Composer({ assets, model, lights, zoom }: { assets: CaveAssets; model: THREE.Object3D; lights: PackedLights; zoom: ZoomDirector }) {
  const gl = useThree((s) => s.gl);
  const scene = useThree((s) => s.scene);
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const size = useThree((s) => s.size);
  const invalidate = useThree((s) => s.invalidate);
  const composer = useRef<EffectComposer | null>(null);
  const startup = useRef<LightStartup | null>(null);

  // Built in an effect, not a memo: StrictMode re-runs effects on the same
  // memoized value, and a disposed composer silently renders nothing.
  useEffect(() => {
    const surfaceShadows = CAVE_FLAGS.shadows ? renderSurfaceShadows(gl, model, lights) : null;
    attachShadows(model, surfaceShadows);
    const shadows = CAVE_FLAGS.haze ? renderSpotShadows(gl, model, assets.manifest.lights) : null;
    // MSAA: sub-pixel geometry (tread-tile edges, railings) and the deck
    // grates' partial coverage (alpha-to-coverage) resolve smoothly, as in
    // Cycles. The stencil buffer keeps the multisampled depth/stencil format
    // blittable into the resolve target (without it the blit fails).
    const next = new EffectComposer(gl, { frameBufferType: THREE.HalfFloatType, stencilBuffer: true, multisampling: CAVE_TUNING.msaa });
    next.addPass(new RenderPass(scene, camera));
    if (CAVE_FLAGS.haze) {
      const haze = new HazeEffect(camera, assets.manifest.mists, assets.manifest.lights, shadows, {
        gain: CAVE_TUNING.hazeGain,
        ambient: CAVE_TUNING.hazeAmbient,
        scale: CAVE_TUNING.hazeScale,
        cull: CAVE_TUNING.hazeCull,
      });
      next.addPass(new EffectPass(camera, haze));
    }
    let beams: BeamEffect | null = null;
    if (!CAVE_FLAGS.haze && CAVE_FLAGS.beams) {
      beams = new BeamEffect(camera, lights, surfaceShadows, assets.manifest.mists, {
        gain: CAVE_TUNING.hazeGain,
        ambient: CAVE_TUNING.hazeAmbient,
      });
      next.addPass(new EffectPass(camera, beams));
    }
    // The white lights power on (flickering) over the first frames; the haze (opt-in) stays fully lit.
    const power = new LightStartup(lights.data, lights.groups, TEXELS_PER_LIGHT, (gains, overall) => beams?.setLevels(gains, overall));
    if (!CAVE_FLAGS.startup || bootSkipped()) power.finish();
    startup.current = power;
    next.addPass(new EffectPass(camera, new PixelFilterEffect()));
    const finish = [];
    if (CAVE_FLAGS.bloom) finish.push(amberBloom(CAVE_TUNING.bloom));
    finish.push(CAVE_FLAGS.logOutput ? new LogEncodeEffect() : new ViewLutEffect(assets.lut));
    next.addPass(new EffectPass(camera, ...finish));
    if (!CAVE_FLAGS.logOutput) next.addPass(new EffectPass(camera, new SMAAEffect()));
    const { width, height } = gl.domElement.getBoundingClientRect();
    next.setSize(width, height);
    composer.current = next;
    zoom.setComposer(next);
    // The canvas renders on demand (camera moves, voxel updates); draw the first frame.
    invalidate();
    if (import.meta.env.DEV) Object.assign(window, { __cave: { gl, scene, camera, composer: next, model, zoom, startup: power } });
    return () => {
      // A remount (HMR, StrictMode) starts from the shared lights: leave them at full power.
      power.finish();
      startup.current = null;
      composer.current = null;
      zoom.setComposer(null);
      next.dispose();
      shadows?.target.dispose();
      attachShadows(model, null);
      surfaceShadows?.target.dispose();
      surfaceShadows?.focus?.target.dispose();
      surfaceShadows?.focus?.data.dispose();
    };
  }, [gl, scene, camera, model, lights, assets, invalidate, zoom]);

  useEffect(() => {
    composer.current?.setSize(size.width, size.height);
    invalidate();
  }, [size, invalidate]);
  // Before the frame renders: the power-on's levels, and another frame while it plays.
  useFrame(() => {
    if (startup.current?.tick(performance.now())) invalidate();
  }, 0);
  // The live scene, or the platform zoom's pre-rendered frames while it animates.
  useFrame((_, delta) => zoom.render(delta), 1);
  return null;
}

function Cave({ assets }: { assets: CaveAssets }) {
  const lights = useMemo(() => applyCaveMaterials(assets), [assets]);
  const gl = useThree((s) => s.gl);
  const scene = useThree((s) => s.scene);
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const invalidate = useThree((s) => s.invalidate);
  const htmlRoot = useThree((s) => s.events.connected) as HTMLElement | undefined;
  // Zooming crops the Blender camera's frame, so it only exists while the camera is locked to it.
  const zoom = useMemo(
    () =>
      new ZoomDirector({
        gl,
        scene,
        camera,
        model: assets.scene,
        shot: assets.manifest.camera,
        hole: assets.manifest.hole,
        html: htmlRoot,
        invalidate,
        enabled: CAVE_FLAGS.locked,
        tunings: zoomLayout,
      }),
    [gl, scene, camera, assets, htmlRoot, invalidate],
  );

  const background = useMemo(() => {
    const [r, g, b] = assets.manifest.world.color;
    const k = assets.manifest.world.strength;
    return linear([r * k, g * k, b * k]);
  }, [assets]);

  return (
    <>
      <CameraFromBlender assets={assets} />
      <CameraView zoom={zoom} />
      <CaveControls assets={assets} />
      <primitive attach="background" object={background} />
      <primitive object={assets.scene} />
      {CAVE_FLAGS.voxels && <VoxelBox hole={assets.manifest.hole} />}
      {CAVE_FLAGS.labels && <CaveLabels />}
      {CAVE_FLAGS.panels && <CavePanels />}
      <Composer assets={assets} model={assets.scene} lights={lights} zoom={zoom} />
    </>
  );
}

/** The Blender cave (`platform-controls/cave-platform-sliders.blend`): baked GI, live direct light. */
export function CaveScene() {
  const [assets, setAssets] = useState<CaveAssets | null>(null);
  useEffect(() => {
    let live = true;
    loadCaveAssets().then((loaded) => live && setAssets(loaded), (error) => console.error("[cave] load failed", error));
    return () => { live = false; };
  }, []);
  return assets ? <Cave assets={assets} /> : null;
}

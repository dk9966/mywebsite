import { Canvas } from "@react-three/fiber";
import * as THREE from "three";
import { CaveScene } from "./components/cave/CaveScene";
import { CAVE_FLAGS } from "./components/cave/caveFlags";
import { CavePanelControls } from "./components/cave/CavePanels";
import { CaveZoomBack } from "./components/cave/CaveZoomBack";
import { CaveZoomControls } from "./components/cave/CaveZoomControls";

/**
 * `/cave` — the Blender cave scene: Cycles' indirect light baked, every
 * light shaded live with soft shadow maps, plus the Voxelize box in the rear hole.
 *
 * `linear` + `flat`: the composer ends in Blender's own view transform (a LUT),
 * so three must neither tone map nor sRGB-encode on top of it.
 *
 * `demand`: the cave is static, so frames are drawn only when the camera moves
 * or the voxel box changes, not 120 times a second. The pixel ratio stops at
 * 1.5: lighting (55 lights, PCSS shadows) and the haze ray-march are per pixel.
 */
export default function CaveApp() {
  return (
    <>
      <Canvas
        linear
        flat
        frameloop={CAVE_FLAGS.continuous ? "always" : "demand"}
        dpr={[1, 1.5]}
        gl={{ antialias: false, powerPreference: "high-performance", outputColorSpace: THREE.LinearSRGBColorSpace }}
        camera={{ fov: 50, near: 0.1, far: 200 }}
      >
        <CaveScene />
      </Canvas>
      {CAVE_FLAGS.locked && <CaveZoomBack />}
      {CAVE_FLAGS.editZoom && <CaveZoomControls />}
      {CAVE_FLAGS.editPanels && <CavePanelControls />}
    </>
  );
}

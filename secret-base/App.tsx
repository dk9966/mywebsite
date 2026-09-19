import { useEffect } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import {
  EffectComposer,
  Bloom,
  N8AO,
  ToneMapping,
  SMAA,
} from "@react-three/postprocessing";
import { ToneMappingMode } from "postprocessing";
import { PortfolioWorld } from "./components/scene/PortfolioWorld";
import { BlenderLens, CameraRig } from "./components/scene/CameraRig";
import { DevExport } from "./components/scene/DevExport";
import { sceneMode } from "./components/scene/sceneMode";
import { StationLightingToggle } from "./components/StationLightingToggle";

const MODE = sceneMode();
const STATION = MODE === "station";

function StationVisibility() {
  const setFrameloop = useThree((state) => state.setFrameloop);
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    const sync = () => {
      setFrameloop(document.hidden ? "never" : "demand");
      if (!document.hidden) invalidate();
    };
    sync();
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, [setFrameloop, invalidate]);
  return null;
}

export default function App() {
  return (
    <>
    <Canvas
      // The station is static between interactions. OrbitControls and React
      // changes request frames, so idle previews need no GPU rendering.
      frameloop={STATION ? "demand" : "always"}
      dpr={[1, 2]}
      gl={{ antialias: !STATION, toneMappingExposure: STATION ? 1.0 : 1.18 }}
      camera={{ fov: 30, near: 0.1, far: 200, position: [16, 12.5, 19] }}
      shadows={false}
    >
      <color attach="background" args={[STATION ? "#000307" : "#0a1630"]} />
      {!STATION && <fog attach="fog" args={["#12234a", 40, 120]} />}
      {STATION && <BlenderLens />}
      {STATION && <StationVisibility />}
      <CameraRig />
      <DevExport />
      <PortfolioWorld />
      {STATION ? (
        <EffectComposer multisampling={4}>
          {/*
            Nothing in the station rig casts a shadow (rect-area lamps never
            can), so vertical and recessed surfaces — the parapet, the deck
            underside, the shaft — come out ~2x brighter than EEVEE's. Two
            screen-space AO passes put that occlusion back: a broad one for the
            deck overhang, a tight one for the contact darkness under the rack
            bases, desk legs and railing posts.
          */}
          <N8AO
            aoRadius={3}
            distanceFalloff={1.2}
            intensity={3.2}
            quality="medium"
            halfRes
          />
          <N8AO
            aoRadius={0.7}
            distanceFalloff={0.5}
            intensity={2}
            quality="medium"
            halfRes
          />
          {/*
            Stands in for the .blend's Glare node (Bloom, strength 0.95), which
            runs on the linear render before AgX — the same order as this pass
            chain. The knee is tighter than Blender's nominal smoothness so the
            rune arcs, which sit only just over the threshold, actually glow.
          */}
          <Bloom
            intensity={0.62}
            luminanceThreshold={0.52}
            luminanceSmoothing={0.15}
            radius={0.72}
            mipmapBlur
          />
          <ToneMapping mode={ToneMappingMode.AGX} />
          <SMAA />
        </EffectComposer>
      ) : (
        <EffectComposer>
          <Bloom intensity={0.6} luminanceThreshold={1.0} mipmapBlur />
        </EffectComposer>
      )}
    </Canvas>
    {STATION && <StationLightingToggle />}
    </>
  );
}

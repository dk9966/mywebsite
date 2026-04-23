import { StrictMode, useCallback } from "react";
import type { ElementRef } from "react";
import { createRoot } from "react-dom/client";
import { Canvas } from "@react-three/fiber";
import { ArcballControls } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import TronGrid from "./components/TronGrid";
import Controls from "./components/Controls";
import { useLineConfig } from "./stores/lineConfig";

function TronPostFX() {
  const cfg = useLineConfig((s) => s.config);
  return (
    <EffectComposer>
      <Bloom
        intensity={cfg.bloomIntensity}
        luminanceThreshold={cfg.bloomThreshold}
        luminanceSmoothing={cfg.bloomSmoothing}
        mipmapBlur
      />
    </EffectComposer>
  );
}

function TronScene() {
  const hideArcGizmos = useCallback((ctrl: ElementRef<typeof ArcballControls> | null) => {
    ctrl?.setGizmosVisible(false);
  }, []);

  return (
    <>
      <color attach="background" args={["#000000"]} />
      <ArcballControls
        ref={hideArcGizmos}
        makeDefault
        target={[2, 1, 2]}
        cursorZoom
        dampingFactor={0.12}
        minDistance={4}
        maxDistance={520}
      />
      <TronGrid />
      <TronPostFX />
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <div
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100%",
      }}
    >
      <Canvas
        style={{ display: "block", width: "100%", height: "100%" }}
        gl={{ antialias: true, alpha: false }}
        camera={{
          position: [42, 30, 46],
          fov: 40,
          near: 0.1,
          far: 400,
        }}
      >
        <TronScene />
      </Canvas>
      <Controls />
    </div>
  </StrictMode>,
);

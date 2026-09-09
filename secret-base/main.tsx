import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Canvas } from "@react-three/fiber";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { PortfolioWorld } from "./components/scene/PortfolioWorld";
import { CameraRig } from "./components/scene/CameraRig";
import { DevExport } from "./components/scene/DevExport";
import { sceneMode } from "./components/scene/sceneMode";

const MODE = sceneMode();
const STATION = MODE === "station";

function App() {
  return (
    <Canvas
      dpr={[1, 2]}
      gl={{ antialias: true, toneMappingExposure: STATION ? 1.0 : 1.18 }}
      camera={{ fov: STATION ? 40 : 30, near: 0.1, far: 200, position: [16, 12.5, 19] }}
      shadows={false}
    >
      <color attach="background" args={[STATION ? "#050508" : "#0a1630"]} />
      {!STATION && <fog attach="fog" args={["#12234a", 40, 120]} />}
      <CameraRig />
      <DevExport />
      <PortfolioWorld />
      <EffectComposer>
        <Bloom
          intensity={STATION ? 0.7 : 0.6}
          luminanceThreshold={1.0}
          mipmapBlur
        />
      </EffectComposer>
    </Canvas>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Canvas } from "@react-three/fiber";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { PortfolioWorld } from "./components/scene/PortfolioWorld";
import { CameraRig } from "./components/scene/CameraRig";
import { DevExport } from "./components/scene/DevExport";

function App() {
  return (
    <Canvas
      dpr={[1, 2]}
      gl={{ antialias: true, toneMappingExposure: 1.18 }}
      camera={{ fov: 30, near: 0.1, far: 200, position: [16, 12.5, 19] }}
      shadows={false}
    >
      <color attach="background" args={["#0a1630"]} />
      <fog attach="fog" args={["#12234a", 40, 120]} />
      <CameraRig />
      <DevExport />
      <PortfolioWorld />
      <EffectComposer>
        <Bloom intensity={0.6} luminanceThreshold={1.0} mipmapBlur />
      </EffectComposer>
    </Canvas>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

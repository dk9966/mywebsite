import { Canvas } from "@react-three/fiber";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import TronGrid from "./components/TronGrid";
import CameraController from "./components/CameraController";
import Controls from "./components/Controls";
import { useLineConfig } from "./stores/lineConfig";

function PostProcessing() {
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

export default function App() {
  return (
    <>
      <Canvas
        gl={{ antialias: true, alpha: false, preserveDrawingBuffer: true }}
        camera={{ position: [0, 0, 60], fov: 50, near: 0.1, far: 500 }}
        style={{ background: "#000" }}
      >
        <color attach="background" args={["#000000"]} />
        <fogExp2 attach="fog" args={["#000000", 0.012]} />
        <CameraController />
        <TronGrid />
        <PostProcessing />
      </Canvas>
      <Controls />
    </>
  );
}

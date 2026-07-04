import { StrictMode, Suspense, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import * as THREE from "three";
import TronCircuitsOutline from "./components/TronCircuitsOutline";
import CircuitsOutlineCamera from "./components/CircuitsOutlineCamera";
import FreeOrbitMouseBindings from "./components/FreeOrbitMouseBindings";
import CircuitSelectionLayer from "./components/CircuitSelection";
import Controls from "./components/Controls";
import CircuitTuner from "./components/CircuitTuner";
import { useCircuitEditShortcuts } from "./hooks/useCircuitEditShortcuts";
import { useLineConfig } from "./stores/lineConfig";
import { useCircuitTuning } from "./stores/circuitTuning";
import { useClock } from "./stores/clock";
import {
  CIRCUITS_OUTLINE_CURSOR_SPEED,
  tronPathsFromCircuitsTraced,
  type CircuitsTracedLayout,
} from "./lib/tronPathsFromCircuitsTraced";

const fallbackLayout = tronPathsFromCircuitsTraced();

const CIRCUITS_CONFIG_OVERRIDES = {
  cursorSpeed: CIRCUITS_OUTLINE_CURSOR_SPEED,
  tipLength: 0.08,
  tipWidth: 0.018,
  tipPointCount: 8,
  bloomIntensity: 2.0,
  bloomThreshold: 0.05,
  gridOpacity: 0,
};

const DEFAULT_FOV = 40;

function CameraFovSync({ fov }: { fov: number }) {
  const camera = useThree((s) => s.camera);
  const invalidate = useThree((s) => s.invalidate);

  useEffect(() => {
    if (camera instanceof THREE.PerspectiveCamera) {
      camera.fov = fov;
      camera.updateProjectionMatrix();
    }
    invalidate();
  }, [camera, fov, invalidate]);

  return null;
}

function TronPostFX() {
  const cfg = useLineConfig((s) => s.config);
  return (
    <EffectComposer>
      <Bloom
        intensity={cfg.bloomIntensity}
        luminanceThreshold={cfg.bloomThreshold}
        luminanceSmoothing={cfg.bloomSmoothing}
        radius={cfg.bloomRadius}
        mipmapBlur
      />
    </EffectComposer>
  );
}

function EditPlaybackFreeze() {
  const isDraggingVertex = useCircuitTuning((s) => s.isDraggingVertex);
  const editTool = useCircuitTuning((s) => s.editTool);
  const selectedLineIds = useCircuitTuning((s) => s.selectedLineIds);
  const editing =
    isDraggingVertex ||
    editTool === "addLine" ||
    (editTool === "select" && selectedLineIds.length > 0);
  const resumePausedRef = useRef<boolean | null>(null);

  useEffect(() => {
    if (editing) {
      if (resumePausedRef.current === null) {
        resumePausedRef.current = useClock.getState().paused;
      }
      useClock.setState({ paused: true, time: useClock.getState().duration });
      return;
    }

    if (resumePausedRef.current !== null) {
      useClock.setState({ paused: resumePausedRef.current });
      resumePausedRef.current = null;
    }
  }, [editing]);

  useFrame(() => {
    if (!editing) return;
    const { time, duration } = useClock.getState();
    if (time !== duration) useClock.setState({ time: duration });
  });

  return null;
}

function CircuitsOutlineScene({
  layout,
  onLayout,
  cinematicMode,
  fov,
}: {
  layout: CircuitsTracedLayout;
  onLayout: (layout: CircuitsTracedLayout) => void;
  cinematicMode: boolean;
  fov: number;
}) {
  useEffect(() => {
    useLineConfig.getState().set(CIRCUITS_CONFIG_OVERRIDES);
  }, []);

  const [cx, cy, cz] = layout.center;

  return (
    <>
      <color attach="background" args={["#000000"]} />
      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.12}
        minDistance={layout.span * 0.06}
        maxDistance={layout.span * 6}
        target={[cx, cy, cz]}
      />
      <FreeOrbitMouseBindings active={!cinematicMode} />
      <Suspense fallback={null}>
        <TronCircuitsOutline
          onLayout={onLayout}
          screenLineWidth={cinematicMode ? undefined : 3}
        />
      </Suspense>
      <EditPlaybackFreeze />
      <CircuitSelectionLayer paths={layout.paths} />
      <CircuitsOutlineCamera
        layout={layout}
        cinematicMode={cinematicMode}
        fov={fov}
      />
      <CameraFovSync fov={fov} />
      <TronPostFX />
    </>
  );
}

function App() {
  useCircuitEditShortcuts();

  const [layout, setLayout] = useState(fallbackLayout);
  const [cinematicMode, setCinematicMode] = useState(true);
  const [fov, setFov] = useState(DEFAULT_FOV);
  const [cx, , cz] = layout.center;
  const camHeight = layout.span * 1.35;

  return (
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
        onPointerMissed={() => useCircuitTuning.getState().select(null)}
        onCreated={(state) => {
          // Wide enough to click thin circuit traces, tight enough to keep
          // neighbouring traces on the dense board distinguishable.
          state.raycaster.params.Line = { threshold: 0.3 };
        }}
        camera={{
          position: [cx, camHeight, cz],
          fov: DEFAULT_FOV,
          near: 0.1,
          far: 500,
        }}
      >
        <CircuitsOutlineScene
          layout={layout}
          onLayout={setLayout}
          cinematicMode={cinematicMode}
          fov={fov}
        />
      </Canvas>
      <Controls
        camera={{
          cinematicMode,
          onCinematicModeChange: setCinematicMode,
          fov,
          onFovChange: setFov,
        }}
      />
      <CircuitTuner paths={layout.paths} />
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

import { StrictMode, Suspense, useCallback, useState } from "react";
import type { ElementRef } from "react";
import { createRoot } from "react-dom/client";
import { Canvas } from "@react-three/fiber";
import { ArcballControls } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import ComponentReferenceOutline from "./components/ComponentReferenceOutline";
import Controls from "./components/Controls";
import { useLineConfig } from "./stores/lineConfig";
import {
  layoutFromPaths,
  type CircuitsTracedLayout,
} from "./lib/tronPathsFromCircuitsTraced";

const fallbackLayout = layoutFromPaths([]);

/** Per wheel notch; default ArcballControls value is 1.1. */
const ZOOM_SCALE_FACTOR = 1.28;

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

function ReferenceOutlineScene({
  layout,
  onLayout,
}: {
  layout: CircuitsTracedLayout;
  onLayout: (layout: CircuitsTracedLayout) => void;
}) {
  const configureArcball = useCallback((ctrl: ElementRef<typeof ArcballControls> | null) => {
    if (!ctrl) return;
    ctrl.setGizmosVisible(false);
    (
      ctrl as unknown as {
        setMouseAction(operation: string, mouse: number | string, key?: string | null): boolean;
      }
    ).setMouseAction("PAN", 0, "SHIFT");
  }, []);

  const [cx, cy, cz] = layout.center;

  return (
    <>
      <color attach="background" args={["#000000"]} />
      <ArcballControls
        ref={configureArcball}
        makeDefault
        target={[cx, cy, cz]}
        cursorZoom
        scaleFactor={ZOOM_SCALE_FACTOR}
        dampingFactor={0.12}
        minDistance={layout.span * 0.35}
        maxDistance={layout.span * 4}
      />
      <Suspense fallback={null}>
        <ComponentReferenceOutline onLayout={onLayout} />
      </Suspense>
      <TronPostFX />
    </>
  );
}

function App() {
  const [layout, setLayout] = useState(fallbackLayout);
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
        camera={{
          position: [cx, camHeight, cz],
          fov: 40,
          near: 0.1,
          far: 500,
        }}
      >
        <ReferenceOutlineScene layout={layout} onLayout={setLayout} />
      </Canvas>
      <Controls />
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

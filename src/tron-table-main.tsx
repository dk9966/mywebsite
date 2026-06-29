import { StrictMode, Suspense, useCallback, useEffect } from "react";
import type { ElementRef } from "react";
import { createRoot } from "react-dom/client";
import { Canvas } from "@react-three/fiber";
import { ArcballControls } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import TronTable from "./components/TronTable";
import Controls from "./components/Controls";
import { useLineConfig } from "./stores/lineConfig";

// Table-scale tuning. The defaults baked into lineConfig assume the 80-unit
// abstract grid; the table is ~3.3m wide so speed and tip dims need an order
// of magnitude tighter. Applied once on mount; the Controls UI can still
// override interactively.
const TABLE_CONFIG_OVERRIDES = {
  cursorSpeed: 2.0,
  tipLength: 0.08,
  tipWidth: 0.015,
  tipPointCount: 6,
  bloomIntensity: 1.4,
  bloomThreshold: 0.1,
  gridOpacity: 0,
};

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

function TableScene() {
  useEffect(() => {
    useLineConfig.getState().set(TABLE_CONFIG_OVERRIDES);
  }, []);

  const configureArcball = useCallback((ctrl: ElementRef<typeof ArcballControls> | null) => {
    if (!ctrl) return;
    ctrl.setGizmosVisible(false);
    (
      ctrl as unknown as {
        setMouseAction(operation: string, mouse: number | string, key?: string | null): boolean;
      }
    ).setMouseAction("PAN", 0, "SHIFT");
  }, []);

  return (
    <>
      <color attach="background" args={["#000000"]} />
      {/* No lights: nothing in the scene needs lighting. The desk mesh is
          deliberately not rendered — only the animated cyan lines are. */}
      <ArcballControls
        ref={configureArcball}
        makeDefault
        // Table centerline at ~y=0.5; the curved front bulges toward -Z
        // (Blender +Y front per blender-table-front.mdc). Camera sits on -Z
        // looking back toward +Z to face the arc.
        target={[0, 0.4, -0.6]}
        cursorZoom
        dampingFactor={0.12}
        minDistance={0.6}
        maxDistance={40}
      />
      <Suspense fallback={null}>
        <TronTable />
      </Suspense>
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
          position: [2.6, 1.6, -2.8],
          fov: 38,
          near: 0.05,
          far: 200,
        }}
      >
        <TableScene />
      </Canvas>
      <Controls />
    </div>
  </StrictMode>,
);

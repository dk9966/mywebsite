import { Environment, MeshReflectorMaterial } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { StrictMode, Suspense, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import * as THREE from "three";
import DeskTable from "./components/DeskTable";
import HudScreen from "./components/HudScreen";
import {
  ClockWidget,
  TelemetryWidget,
  TerminalWidget,
} from "./components/hudWidgets";
const DEFAULT_CAMERA_POS: [number, number, number] = [0, 2, 0.45];

const DEFAULT_LOOK_AT: [number, number, number] = [0, 1.68, -1.0];

const DEFAULT_FOV = 62;
const DEFAULT_NEAR = 0.05;
const DEFAULT_FAR = 100;

/** Screens sit on this plane (less negative z = closer to the seated camera). */
const HUD_Z = -1.05;

type DeskSceneProps = {
  cameraPosition: [number, number, number];
  lookAtCoords: [number, number, number];
  cameraFov: number;
  cameraNear: number;
  cameraFar: number;
};

function DeskScene({
  cameraPosition,
  lookAtCoords,
  cameraFov,
  cameraNear,
  cameraFar,
}: DeskSceneProps) {
  return (
    <>
      <color attach="background" args={["#05080b"]} />
      <fog attach="fog" args={["#05080b", 6, 22]} />

      {/* IBL so the polished desk and floor have something to reflect.
          Warehouse reads as a dim factory shell — cool grey gradient, no
          warm tint to fight the practicals overhead. Kept dim because the
          point lights below carry the direct illumination. */}
      <Environment preset="warehouse" environmentIntensity={0.5} />

      <ambientLight intensity={0.18} color="#bcd6e0" />

      {/* Three ceiling practicals above the desk — two flanking the work
          surface and one pushed forward over the user. With decay=2 the
          intensity is candela-ish; values look big but settle to a
          comfortable level by the time they reach the desk top (y≈1.05).
          Each pointLight is paired with a Bulb mesh so the reflective floor
          below has a bright shape to mirror — that's what sells the
          Stark-workshop pool halos. */}
      <Bulb
        position={[-1.1, 4.6, -0.3]}
        color="#eef4f7"
        intensity={120}
        distance={14}
      />
      <Bulb
        position={[1.1, 4.6, -0.3]}
        color="#eef4f7"
        intensity={120}
        distance={14}
      />
      <Bulb
        position={[0, 4.6, 0.9]}
        color="#cfe2eb"
        intensity={70}
        distance={13}
      />

      {/* Soft directional from above for surface modelling — gives the desk
          top a clear plane and the leg fronts a subtle gradient. */}
      <directionalLight
        position={[0.4, 6, 1]}
        intensity={1.6}
        color="#dde8ee"
      />

      <Suspense fallback={null}>
        <DeskTable />
      </Suspense>
      <Floor />

      <CameraParamsSync fov={cameraFov} near={cameraNear} far={cameraFar} />

      <HeadLook
        position={cameraPosition}
        lookAt={lookAtCoords}
        yawClamp={Math.PI * 0.45}
        pitchMin={-Math.PI * 0.32}
        pitchMax={Math.PI * 0.18}
      />

      <HudScreens />

      {/* Subtle bloom so the practicals bleed into halos in both the direct
          view and the floor reflection — that's what reads as the polished
          Stark-workshop look rather than three pinpoint dots. Threshold is
          near 1.0 so only the un-tone-mapped bulb meshes glow; the cyan
          HUD text stays crisp. */}
      <EffectComposer>
        <Bloom
          mipmapBlur
          intensity={0.85}
          luminanceThreshold={0.9}
          luminanceSmoothing={0.15}
          radius={0.7}
        />
      </EffectComposer>
    </>
  );
}

function CameraParamsSync({
  fov,
  near,
  far,
}: {
  fov: number;
  near: number;
  far: number;
}) {
  const camera = useThree((s) => s.camera);
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    /* Three.js PerspectiveCamera is mutated in-place; this is idiomatic R3F. */
    if (camera instanceof THREE.PerspectiveCamera) {
      /* eslint-disable react-hooks/immutability -- PerspectiveCamera wired by R3F */
      camera.fov = fov;
      camera.near = near;
      camera.far = far;
      /* eslint-enable react-hooks/immutability */
      camera.updateProjectionMatrix();
    }
    invalidate();
  }, [camera, fov, near, far, invalidate]);
  return null;
}

// A practical bulb + its pointLight, co-located. The visible sphere is
// what the floor's planar reflection mirrors back as a halo; the light
// behind it does the actual lighting work. toneMapped={false} keeps the
// bulb reading as a true highlight after ACES tone mapping.
type BulbProps = {
  position: [number, number, number];
  color: string;
  intensity: number;
  distance: number;
};

function Bulb({ position, color, intensity, distance }: BulbProps) {
  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.12, 24, 24]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
      <pointLight
        intensity={intensity}
        color={color}
        distance={distance}
        decay={2}
      />
    </group>
  );
}

// Wet-concrete workshop floor at y=0, where the GLB's foot braces rest.
// MeshReflectorMaterial renders a planar reflection from a virtual camera
// each frame, then blurs and mixes it back; we keep the resolution modest
// and the blur generous so the bulbs above show up as soft, elongated
// pools rather than a sharp mirror image of the scene.
function Floor() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
      <planeGeometry args={[40, 40]} />
      <MeshReflectorMaterial
        resolution={1024}
        blur={[120, 40]}
        mixBlur={0.6}
        mixStrength={1.3}
        mixContrast={1.2}
        depthScale={1}
        minDepthThreshold={0.85}
        maxDepthThreshold={1}
        color="#080c10"
        metalness={0.75}
        roughness={0.55}
      />
    </mesh>
  );
}

// First-person look-around. The camera stays planted at `position` and the
// drag gesture only rotates it — like a seated user turning their head
// instead of orbiting the scene. Replaces drei's OrbitControls, which keeps
// `target` fixed and moves the camera around it.
//
// We listen on the canvas element directly so HTML panel drags (which target
// the panel divs in the CSS3D layer) never trigger a head turn.
type HeadLookProps = {
  position: [number, number, number];
  lookAt: [number, number, number];
  yawClamp?: number;
  pitchMin?: number;
  pitchMax?: number;
  sensitivity?: number;
};

function HeadLook({
  position,
  lookAt,
  yawClamp,
  pitchMin = -Math.PI / 3,
  pitchMax = Math.PI / 3,
  sensitivity = 0.0035,
}: HeadLookProps) {
  const camera = useThree((s) => s.camera);
  const gl = useThree((s) => s.gl);

  const yawRef = useRef(0);
  const pitchRef = useRef(0);
  const initialYawRef = useRef(0);
  const drag = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    startYaw: number;
    startPitch: number;
  } | null>(null);

  useEffect(() => {
    camera.position.set(...position);
  }, [camera, position]);

  // Re-base head orientation when lookAt identity changes.
  useEffect(() => {
    camera.up.set(0, 1, 0);
    camera.lookAt(...lookAt);
    const euler = new THREE.Euler().setFromQuaternion(camera.quaternion, "YXZ");
    yawRef.current = euler.y;
    pitchRef.current = euler.x;
    initialYawRef.current = euler.y;
  }, [camera, lookAt]);

  useEffect(() => {
    const canvas = gl.domElement;

    const apply = () => {
      const euler = new THREE.Euler(pitchRef.current, yawRef.current, 0, "YXZ");
      camera.quaternion.setFromEuler(euler);
    };

    const onPointerDown = (e: PointerEvent) => {
      // Ignore non-primary buttons so right-click / middle-click are free.
      if (e.button !== 0) return;
      drag.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        startYaw: yawRef.current,
        startPitch: pitchRef.current,
      };
      canvas.setPointerCapture(e.pointerId);
    };

    const onPointerMove = (e: PointerEvent) => {
      const d = drag.current;
      if (!d || d.pointerId !== e.pointerId) return;
      const dx = e.clientX - d.startX;
      const dy = e.clientY - d.startY;

      let nextYaw = d.startYaw - dx * sensitivity;
      let nextPitch = d.startPitch - dy * sensitivity;

      if (yawClamp != null) {
        const lo = initialYawRef.current - yawClamp;
        const hi = initialYawRef.current + yawClamp;
        nextYaw = Math.max(lo, Math.min(hi, nextYaw));
      }
      nextPitch = Math.max(pitchMin, Math.min(pitchMax, nextPitch));

      yawRef.current = nextYaw;
      pitchRef.current = nextPitch;
      apply();
    };

    const endDrag = (e: PointerEvent) => {
      if (drag.current?.pointerId !== e.pointerId) return;
      drag.current = null;
      try {
        canvas.releasePointerCapture(e.pointerId);
      } catch {
        // releasePointerCapture throws if the pointer is already gone; safe to ignore.
      }
    };

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);

    return () => {
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", endDrag);
      canvas.removeEventListener("pointercancel", endDrag);
      canvas.style.cursor = "";
    };
  }, [camera, gl, sensitivity, yawClamp, pitchMin, pitchMax]);

  return null;
}

// Three screens in one row, slightly closer to the seated camera than the
// previous 6-up layout. Y is lifted so panels clear the desk top (y≈1.05);
// Html backdrop-filter would otherwise smear the cyan desk lines.
function HudScreens() {
  const y = 1.68;
  const z = HUD_Z;
  return (
    <>
      <HudScreen
        position={[-1.0, y, z]}
        widthPx={420}
        heightPx={280}
        title="Telemetry"
        tag="01"
      >
        <TelemetryWidget />
      </HudScreen>

      <HudScreen
        position={[0.0, y, z]}
        widthPx={520}
        heightPx={260}
        title="MCP Trace"
        tag="02"
      >
        <TerminalWidget />
      </HudScreen>

      <HudScreen
        position={[1.0, y, z]}
        widthPx={420}
        heightPx={280}
        title="Chrono"
        tag="00"
      >
        <ClockWidget />
      </HudScreen>
    </>
  );
}

export function DeskSetupApp() {
  const cameraPos = DEFAULT_CAMERA_POS;
  const lookAtCoords = DEFAULT_LOOK_AT;
  const fov = DEFAULT_FOV;
  const near = DEFAULT_NEAR;
  const far = DEFAULT_FAR;

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
          position: [...cameraPos],
          fov,
          near,
          far,
        }}
      >
        <DeskScene
          cameraPosition={cameraPos}
          lookAtCoords={lookAtCoords}
          cameraFov={fov}
          cameraNear={near}
          cameraFar={far}
        />
      </Canvas>
      <Hint />
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <DeskSetupApp />
  </StrictMode>,
);

function Hint() {
  return (
    <div
      style={{
        position: "absolute",
        left: 16,
        bottom: 14,
        color: "rgba(174, 234, 238, 0.55)",
        fontSize: 11,
        letterSpacing: "0.22em",
        textTransform: "uppercase",
        pointerEvents: "none",
        lineHeight: 1.5,
      }}
    >
      <div>Drag edges to move · corners to resize</div>
      <div>Drag empty space to look around</div>
    </div>
  );
}

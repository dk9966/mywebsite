import { Line, PerspectiveCamera } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { VariantEntry } from "../lib/qfpVariantCatalog";

const ROTATION_SPEED = 0.95;

function RotatingOutline({
  variant,
  color,
}: {
  variant: VariantEntry;
  color: string;
}) {
  const groupRef = useRef<THREE.Group>(null);

  const framing = useMemo(() => {
    const { w, d, h } = variant.natural;
    const span = Math.max(w, d, h, 0.4);
    const dist = span * 2.35;
    return {
      lookAt: new THREE.Vector3(0, h * 0.42, 0),
      position: new THREE.Vector3(dist * 0.72, dist * 0.58, dist * 0.72),
    };
  }, [variant.natural]);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * ROTATION_SPEED;
    }
  });

  return (
    <>
      <PerspectiveCamera
        makeDefault
        position={framing.position}
        fov={32}
        near={0.01}
        far={100}
        onUpdate={(cam) => cam.lookAt(framing.lookAt)}
      />
      <group ref={groupRef}>
        {variant.polylines.map((poly, i) =>
          poly.length >= 2 ? (
            <Line
              key={i}
              points={poly}
              color={color}
              lineWidth={2}
              transparent
              opacity={0.95}
            />
          ) : null,
        )}
      </group>
    </>
  );
}

export default function MeshVariantPreview({
  variant,
  color,
}: {
  variant: VariantEntry;
  color: string;
}) {
  return (
    <Canvas
      className="c3d__variant-preview-canvas"
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
    >
      <color attach="background" args={["#04090b"]} />
      <RotatingOutline variant={variant} color={color} />
    </Canvas>
  );
}

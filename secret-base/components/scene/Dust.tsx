import { useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";

const fract = (n: number) => n - Math.floor(n);

/** Slowly drifting dust motes filling the cavern air. Deterministic layout. */
export function Dust({ count = 260 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null);

  const geometry = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const a = (i + 1) * 12.9898;
      pos[i * 3] = (fract(Math.sin(a) * 43758.5453) - 0.5) * 46;
      pos[i * 3 + 1] = fract(Math.sin(a * 1.7) * 24634.6345) * 24 - 12;
      pos[i * 3 + 2] = (fract(Math.sin(a * 2.3) * 8812.421) - 0.5) * 42;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    return g;
  }, [count]);

  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.008;
  });

  return (
    <points ref={ref} geometry={geometry} frustumCulled={false}>
      <pointsMaterial
        color="#7fd4ff"
        size={0.07}
        sizeAttenuation
        transparent
        opacity={0.45}
        depthWrite={false}
      />
    </points>
  );
}

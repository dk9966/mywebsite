import { useMemo } from "react";
import * as THREE from "three";
import { graphiteDark } from "./materials";

type Vec3 = [number, number, number];

function makeSignTexture(text: string): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 256;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#0b1120";
  ctx.fillRect(0, 0, 1024, 256);
  ctx.strokeStyle = "#2bd9f6";
  ctx.lineWidth = 8;
  ctx.strokeRect(12, 12, 1000, 232);
  ctx.fillStyle = "#eef6ff";
  ctx.font =
    "bold 118px 'Segoe UI', 'Helvetica Neue', Arial, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text.toUpperCase(), 512, 136);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

/** Readable island sign: dark panel, cyan border, unlit text texture. */
export function Sign({
  text,
  width = 3,
  position,
  rotation = [0, 0, 0],
  postHeight = 1.1,
  posts = true,
}: {
  text: string;
  width?: number;
  position: Vec3;
  rotation?: Vec3;
  postHeight?: number;
  posts?: boolean;
}) {
  const texture = useMemo(() => makeSignTexture(text), [text]);
  const h = width / 4;
  return (
    <group position={position} rotation={rotation} name={`sign-${text}`}>
      <mesh material={graphiteDark} position={[0, 0, -0.07]}>
        <boxGeometry args={[width + 0.18, h + 0.18, 0.12]} />
      </mesh>
      <mesh>
        <planeGeometry args={[width, h]} />
        <meshBasicMaterial map={texture} toneMapped={false} />
      </mesh>
      {posts && (
        <>
          <mesh
            material={graphiteDark}
            position={[-width / 2 + 0.2, -h / 2 - postHeight / 2, -0.07]}
          >
            <boxGeometry args={[0.11, postHeight, 0.11]} />
          </mesh>
          <mesh
            material={graphiteDark}
            position={[width / 2 - 0.2, -h / 2 - postHeight / 2, -0.07]}
          >
            <boxGeometry args={[0.11, postHeight, 0.11]} />
          </mesh>
        </>
      )}
    </group>
  );
}

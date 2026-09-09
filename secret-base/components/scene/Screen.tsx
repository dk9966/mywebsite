import { useMemo } from "react";
import * as THREE from "three";
import { graphiteDark } from "./materials";

type Vec3 = [number, number, number];

export type ScreenVariant = "ui" | "avatar" | "envelope" | "card" | "radar";

function drawScreen(variant: ScreenVariant): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = variant === "radar" ? 512 : 320;
  const ctx = canvas.getContext("2d")!;
  const W = canvas.width;
  const H = canvas.height;

  const bg = variant === "envelope" ? "#241e66" : "#0a1c3f";
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);
  if (variant !== "radar") {
    ctx.strokeStyle = "#5fb2ff";
    ctx.lineWidth = 6;
    ctx.strokeRect(8, 8, W - 16, H - 16);
  }

  ctx.fillStyle = "#7cc4ff";
  ctx.strokeStyle = "#7cc4ff";

  if (variant === "radar") {
    // circular readout: concentric rings, cross-hairs, sweep, blips
    const cx = W / 2;
    const cy = H / 2;
    ctx.lineWidth = 5;
    [70, 130, 190, 240].forEach((r) => {
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
    });
    ctx.lineWidth = 3;
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.moveTo(cx - 240, cy);
    ctx.lineTo(cx + 240, cy);
    ctx.moveTo(cx, cy - 240);
    ctx.lineTo(cx, cy + 240);
    ctx.stroke();
    // sweep wedge
    ctx.globalAlpha = 0.35;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, 235, -0.4, 0.55);
    ctx.closePath();
    ctx.fill();
    // blips
    ctx.globalAlpha = 1;
    [
      [110, -60],
      [-80, 95],
      [40, 160],
      [-150, -110],
    ].forEach(([dx, dy]) => {
      ctx.beginPath();
      ctx.arc(cx + dx, cy + dy, 9, 0, Math.PI * 2);
      ctx.fill();
    });
    return canvas;
  }

  if (variant === "ui") {
    // header bar + rows of UI-like lines + a small hex widget
    ctx.fillRect(28, 28, 200, 18);
    for (let i = 0; i < 6; i++) {
      const w = 150 + ((i * 73) % 130);
      ctx.globalAlpha = 0.75;
      ctx.fillRect(28, 70 + i * 34, w, 10);
    }
    ctx.globalAlpha = 1;
    ctx.lineWidth = 8;
    ctx.beginPath();
    ctx.arc(410, 150, 58, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(410, 150, 30, 0, Math.PI * 1.4);
    ctx.stroke();
  } else if (variant === "avatar") {
    // person silhouette
    ctx.beginPath();
    ctx.arc(W / 2, 110, 52, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(W / 2, 255, 92, Math.PI, 0);
    ctx.fill();
    ctx.fillRect(W / 2 - 92, 255, 184, 30);
  } else if (variant === "envelope") {
    ctx.fillStyle = "#cdd6ff";
    const x = 116, y = 80, w = 280, h = 170;
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = "#241e66";
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.moveTo(x, y + 6);
    ctx.lineTo(x + w / 2, y + h / 2 + 10);
    ctx.lineTo(x + w, y + 6);
    ctx.stroke();
  } else {
    // card: avatar bust + text lines (experience wall cards)
    ctx.beginPath();
    ctx.arc(W / 2, 96, 44, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(W / 2, 210, 72, Math.PI, 0);
    ctx.fill();
    ctx.globalAlpha = 0.7;
    ctx.fillRect(96, 248, 320, 12);
    ctx.fillRect(136, 276, 240, 12);
    ctx.globalAlpha = 1;
  }
  return canvas;
}

function ScreenFace({
  texture,
  glow = 0,
  transparent = false,
}: {
  texture: THREE.Texture;
  glow?: number;
  transparent?: boolean;
}) {
  if (glow > 0) {
    return (
      <meshStandardMaterial
        map={texture}
        color="#000000"
        emissive="#ffffff"
        emissiveMap={texture}
        emissiveIntensity={glow}
        roughness={1}
        metalness={0}
        toneMapped={false}
        transparent={transparent}
        depthWrite={!transparent}
        side={transparent ? THREE.DoubleSide : THREE.FrontSide}
      />
    );
  }
  return <meshBasicMaterial map={texture} toneMapped={false} />;
}

/** Emissive UI screen with a dark frame and optional stand. */
export function Screen({
  variant = "ui",
  width = 2,
  height = 1.25,
  position,
  rotation = [0, 0, 0],
  stand = false,
  frame = true,
  round = false,
  glow = 0,
  transparent = false,
}: {
  variant?: ScreenVariant;
  width?: number;
  height?: number;
  position: Vec3;
  rotation?: Vec3;
  stand?: boolean;
  frame?: boolean;
  /** circular screen: uses `width` as diameter, ignores `height` */
  round?: boolean;
  /** emissive intensity; values above ~1 trip the scene bloom */
  glow?: number;
  transparent?: boolean;
}) {
  const texture = useMemo(() => {
    const tex = new THREE.CanvasTexture(drawScreen(variant));
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
    return tex;
  }, [variant]);

  if (round) {
    return (
      <group position={position} rotation={rotation}>
        {frame && (
          <mesh
            material={graphiteDark}
            position={[0, 0, -0.05]}
            rotation={[Math.PI / 2, 0, 0]}
          >
            <cylinderGeometry
              args={[width / 2 + 0.09, width / 2 + 0.09, 0.08, 24]}
            />
          </mesh>
        )}
        <mesh>
          <circleGeometry args={[width / 2, 32]} />
          <ScreenFace texture={texture} glow={glow} transparent={transparent} />
        </mesh>
      </group>
    );
  }

  return (
    <group position={position} rotation={rotation}>
      {frame && (
        <mesh material={graphiteDark} position={[0, 0, -0.06]}>
          <boxGeometry args={[width + 0.16, height + 0.16, 0.1]} />
        </mesh>
      )}
      <mesh>
        <planeGeometry args={[width, height]} />
        <ScreenFace texture={texture} glow={glow} transparent={transparent} />
      </mesh>
      {stand && (
        <>
          <mesh material={graphiteDark} position={[0, -height / 2 - 0.3, -0.08]}>
            <boxGeometry args={[0.14, 0.65, 0.14]} />
          </mesh>
          <mesh material={graphiteDark} position={[0, -height / 2 - 0.62, -0.08]}>
            <boxGeometry args={[0.7, 0.08, 0.45]} />
          </mesh>
        </>
      )}
    </group>
  );
}

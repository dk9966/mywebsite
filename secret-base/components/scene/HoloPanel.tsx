import { useMemo } from "react";
import * as THREE from "three";
import { projects } from "../../../src/data/resume";

type Vec3 = [number, number, number];

const W = 1360;
const H = 820;

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
  maxLines: number,
) {
  const words = text.split(" ");
  let line = "";
  let lines = 0;
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && line) {
      ctx.fillText(line, x, y + lines * lineHeight);
      lines++;
      line = word;
      if (lines >= maxLines - 1) break;
    } else {
      line = test;
    }
  }
  if (lines < maxLines) ctx.fillText(line, x, y + lines * lineHeight);
}

function drawIcon(
  ctx: CanvasRenderingContext2D,
  index: number,
  cx: number,
  cy: number,
) {
  ctx.strokeStyle = "#9db9ff";
  ctx.fillStyle = "#9db9ff";
  ctx.lineWidth = 5;
  if (index === 0) {
    // mahjong tile
    roundRect(ctx, cx - 45, cy - 62, 90, 124, 12);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, 26, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, 8, 0, Math.PI * 2);
    ctx.fill();
  } else {
    // AI chip
    ctx.strokeRect(cx - 48, cy - 48, 96, 96);
    ctx.strokeRect(cx - 24, cy - 24, 48, 48);
    for (let i = -1; i <= 1; i++) {
      ctx.beginPath();
      ctx.moveTo(cx + i * 28, cy - 48);
      ctx.lineTo(cx + i * 28, cy - 70);
      ctx.moveTo(cx + i * 28, cy + 48);
      ctx.lineTo(cx + i * 28, cy + 70);
      ctx.moveTo(cx - 48, cy + i * 28);
      ctx.lineTo(cx - 70, cy + i * 28);
      ctx.moveTo(cx + 48, cy + i * 28);
      ctx.lineTo(cx + 70, cy + i * 28);
      ctx.stroke();
    }
  }
}

function drawPanel(): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d")!;

  // translucent holo body + glowing border
  roundRect(ctx, 10, 10, W - 20, H - 20, 26);
  ctx.fillStyle = "rgba(14, 36, 104, 0.85)";
  ctx.fill();
  ctx.strokeStyle = "rgba(90, 150, 255, 0.45)";
  ctx.lineWidth = 16;
  ctx.stroke();
  ctx.strokeStyle = "#74aaff";
  ctx.lineWidth = 6;
  ctx.stroke();

  // header
  ctx.fillStyle = "#eef4ff";
  ctx.font = "bold 46px 'Segoe UI', 'Helvetica Neue', Arial, sans-serif";
  ctx.textBaseline = "middle";
  ctx.fillText("FEATURED PROJECTS", 64, 84);
  ctx.strokeStyle = "rgba(140, 180, 255, 0.5)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(60, 124);
  ctx.lineTo(560, 124);
  ctx.stroke();

  // project cards (from the resume)
  const cardY = 160;
  const cardH = 570;
  const cardW = 396;
  projects.slice(0, 2).forEach((p, i) => {
    const x = 60 + i * (cardW + 32);
    roundRect(ctx, x, cardY, cardW, cardH, 18);
    ctx.fillStyle = "rgba(30, 64, 158, 0.5)";
    ctx.fill();
    ctx.strokeStyle = "rgba(140, 180, 255, 0.55)";
    ctx.lineWidth = 3;
    ctx.stroke();

    drawIcon(ctx, i, x + cardW / 2, cardY + 118);

    ctx.fillStyle = "#eef4ff";
    let titleSize = 30;
    const title = p.name.toUpperCase();
    do {
      ctx.font = `bold ${titleSize}px 'Segoe UI', Arial, sans-serif`;
      titleSize -= 1;
    } while (ctx.measureText(title).width > cardW - 56 && titleSize > 16);
    ctx.fillText(title, x + 28, cardY + 242);

    ctx.fillStyle = "#c6d9ff";
    ctx.font = "22px 'Segoe UI', Arial, sans-serif";
    wrapText(ctx, p.tagline, x + 28, cardY + 290, cardW - 56, 30, 4);

    ctx.fillStyle = "#7cd7ff";
    ctx.font = "20px 'Segoe UI', Arial, sans-serif";
    wrapText(ctx, p.stack.join(" · "), x + 28, cardY + 412, cardW - 56, 26, 2);

    ctx.fillStyle = "#9db9ff";
    ctx.font = "18px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(`${p.context} · ${p.period}`, x + 28, cardY + 462);

    roundRect(ctx, x + 28, cardY + 490, 208, 54, 10);
    ctx.strokeStyle = "#9dc0ff";
    ctx.lineWidth = 3;
    ctx.stroke();
    ctx.fillStyle = "#dbe9ff";
    ctx.font = "bold 21px 'Segoe UI', Arial, sans-serif";
    ctx.fillText("VIEW PROJECT", x + 52, cardY + 518);
  });

  // right column: system status + activity feed
  const colX = 940;
  const colW = 360;
  roundRect(ctx, colX, 160, colW, 250, 18);
  ctx.fillStyle = "rgba(30, 64, 158, 0.5)";
  ctx.fill();
  ctx.strokeStyle = "rgba(140, 180, 255, 0.55)";
  ctx.lineWidth = 3;
  ctx.stroke();
  ctx.fillStyle = "#eef4ff";
  ctx.font = "bold 24px 'Segoe UI', Arial, sans-serif";
  ctx.fillText("SYSTEM STATUS", colX + 26, 200);
  const statusRows: [string, string, string][] = [
    ["NETWORK", "Online", "#4ade80"],
    ["CPU", "42%", "#67e8f9"],
    ["MEMORY", "68%", "#67e8f9"],
  ];
  statusRows.forEach(([k, v, c], i) => {
    const y = 248 + i * 52;
    ctx.fillStyle = "#c6d9ff";
    ctx.font = "21px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(k, colX + 26, y);
    ctx.fillStyle = c;
    ctx.font = "bold 21px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(v, colX + colW - 110, y);
    ctx.strokeStyle = "rgba(140,180,255,0.25)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(colX + 26, y + 24);
    ctx.lineTo(colX + colW - 26, y + 24);
    ctx.stroke();
  });

  roundRect(ctx, colX, 440, colW, 290, 18);
  ctx.fillStyle = "rgba(30, 64, 158, 0.5)";
  ctx.fill();
  ctx.strokeStyle = "rgba(140, 180, 255, 0.55)";
  ctx.lineWidth = 3;
  ctx.stroke();
  ctx.fillStyle = "#eef4ff";
  ctx.font = "bold 24px 'Segoe UI', Arial, sans-serif";
  ctx.fillText("ACTIVITY FEED", colX + 26, 480);
  const feed: [string, string][] = [
    ["Build Complete", "2m ago"],
    ["Test Passed", "11m ago"],
    ["Deploy Ready", "1h ago"],
  ];
  feed.forEach(([label, when], i) => {
    const y = 530 + i * 62;
    ctx.strokeStyle = "#4ade80";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(colX + colW - 46, y - 4, 13, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(colX + colW - 52, y - 4);
    ctx.lineTo(colX + colW - 47, y + 2);
    ctx.lineTo(colX + colW - 39, y - 10);
    ctx.stroke();
    ctx.fillStyle = "#dbe9ff";
    ctx.font = "bold 21px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(label, colX + 26, y - 8);
    ctx.fillStyle = "#8aa6d6";
    ctx.font = "18px 'Segoe UI', Arial, sans-serif";
    ctx.fillText(when, colX + 26, y + 18);
  });

  return canvas;
}

/**
 * Large translucent hologram listing the resume's featured projects,
 * projected up from the Projects pedestal (per the reference image).
 */
export function HoloPanel({
  position,
  rotation = [0, 0, 0],
  width = 5.6,
}: {
  position: Vec3;
  rotation?: Vec3;
  width?: number;
}) {
  const texture = useMemo(() => {
    const tex = new THREE.CanvasTexture(drawPanel());
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    return tex;
  }, []);

  const height = (width * H) / W;

  return (
    <group position={position} rotation={rotation} name="holoPanel">
      <mesh>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          map={texture}
          transparent
          toneMapped={false}
          side={THREE.DoubleSide}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

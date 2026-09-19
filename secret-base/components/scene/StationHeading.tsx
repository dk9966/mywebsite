import { useEffect, useRef } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { loadStationFont, STATION_FONTS } from "./stationFonts";

const HEADING_FONT = STATION_FONTS.find((font) => font.name === "Chakra Petch")!;

/** A transparent emissive texture sits in the same world plane as the centre panel. */
export function StationHeading({ lightColor, title = "Projects", width = 5.7 }: { lightColor: THREE.Color; title?: string; width?: number }) {
  const invalidate = useThree((s) => s.invalidate);
  const material = useRef<THREE.MeshBasicMaterial>(null);
  useEffect(() => {
    if (!material.current) return;
    const surface = material.current;
    const canvas = document.createElement("canvas");
    canvas.width = 4096;
    canvas.height = 896;
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = 16;
    surface.map = texture;
    surface.needsUpdate = true;
    let current = true;
    const font = HEADING_FONT;
    const draw = (family: string) => {
      if (!current) return;
      const ctx = canvas.getContext("2d")!;
      ctx.setTransform(2, 0, 0, 2, 0, 0);
      ctx.clearRect(0, 0, 2048, 448);
      ctx.font = `${font.weight} 238px ${family}`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.letterSpacing = "12px";
      ctx.fillStyle = "#ffffff";
      // Scale uniformly for wide faces, preserving their natural proportions.
      const fit = Math.min(1, 1780 / ctx.measureText(title).width);
      ctx.save();
      ctx.translate(1024, 224);
      ctx.scale(fit, fit);
      ctx.fillText(title, 0, 0);
      ctx.restore();
      ctx.letterSpacing = "0px";
      texture.needsUpdate = true;
      invalidate();
    };
    // Keep the heading present while the local font is loading.
    draw("sans-serif");
    void loadStationFont(font).then(() => draw(`"Station ${font.name}"`)).catch(() => draw("sans-serif"));
    return () => {
      current = false;
      surface.map = null;
      texture.dispose();
    };
  }, [invalidate, title]);

  return (
    <group name={`stationHeading_${title}`}>
      <mesh renderOrder={3}>
        <planeGeometry args={[width, width * 1.2468 / 5.7]} />
        <meshBasicMaterial ref={material} color={lightColor} transparent depthWrite={false} toneMapped={false} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

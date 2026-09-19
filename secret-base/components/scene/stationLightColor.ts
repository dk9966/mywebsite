import * as THREE from "three";
import { create } from "zustand";

const KEY = "station-light-blue-v2";
const DEFAULT = { hue: 50, tint: 0 };
function initial() {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) ?? "null");
    return {
      hue: Number.isFinite(value?.hue) ? Math.max(0, Math.min(100, value.hue)) : DEFAULT.hue,
      tint: Number.isFinite(value?.tint) ? Math.max(-100, Math.min(100, value.tint)) : DEFAULT.tint,
    };
  } catch { return DEFAULT; }
}
export const useStationLightColor = create<{
  hue: number; tint: number; change: (key: "hue" | "tint", value: number) => void;
}>((set) => ({
  ...initial(),
  change: (key, value) => {
    if (!Number.isFinite(value)) return;
    set((state) => {
      const next = { hue: state.hue, tint: state.tint, [key]: Math.max(key === "hue" ? 0 : -100, Math.min(100, value)) };
      try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* Optional storage. */ }
      return next;
    });
  },
}));

/** Blue-only range: authored pale cyan → deck_huge neon → deck_huge floor rings.
 * References read from base.blend in linear RGB. Keep each emitter's HDR peak
 * and intensity so the existing spatial gradients and light balance survive. */
export function stationLightColor(source: THREE.Color, hue: number, tint: number) {
  const peak = Math.max(source.r, source.g, source.b);
  if (peak === 0) return source.clone();
  const paleCyan = new THREE.Color().setRGB(0.41025641, 0.76923077, 1, THREE.LinearSRGBColorSpace);
  const deckNeon = new THREE.Color().setRGB(0.06, 0.55, 1, THREE.LinearSRGBColorSpace);
  const deckRings = new THREE.Color().setRGB(0.02, 0.13, 1, THREE.LinearSRGBColorSpace);
  const amount = THREE.MathUtils.clamp(hue, 0, 100);
  const color = amount <= 50
    ? paleCyan.lerp(deckNeon, amount / 50)
    : deckNeon.lerp(deckRings, (amount - 50) / 50);
  const tintAmount = THREE.MathUtils.clamp(tint, -100, 100) / 100;
  if (tintAmount < 0) color.lerp(new THREE.Color(1, 1, 1), -tintAmount * 0.85);
  else color.lerp(deckRings, tintAmount * 0.8);
  return color.multiplyScalar(peak);
}

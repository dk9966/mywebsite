export type SceneMode = "baked" | "procedural" | "station";

/** Which world `/secret-base/` should load. Read once at boot. */
export function sceneMode(): SceneMode {
  if (typeof window === "undefined") return "baked";
  const q = new URLSearchParams(window.location.search);
  if (q.has("station")) return "station";
  if (q.has("procedural")) return "procedural";
  return "baked";
}

export type CaveRoute = "desk" | "cave" | "cave-title";

/** `/cave` plays the title rez. `/cave-title` is the same scene plus the tuner. */
export function caveRoute(): CaveRoute {
  if (typeof window === "undefined") return "desk";
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/cave-title" || path.endsWith("/cave-title")) return "cave-title";
  if (path === "/cave" || path.endsWith("/cave")) return "cave";
  return "desk";
}

export function isCaveTitles(): boolean {
  const route = caveRoute();
  return route === "cave" || route === "cave-title";
}

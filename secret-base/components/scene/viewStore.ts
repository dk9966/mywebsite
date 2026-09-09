import { create } from "zustand";
import { sceneMode } from "./sceneMode";

export type ViewName = "overview" | "projects" | "about" | "station";

/** Which camera view the scene is in. Click an island to toggle its view. */
export const useViewStore = create<{
  view: ViewName;
  setView: (view: ViewName) => void;
  toggleView: (view: Exclude<ViewName, "overview" | "station">) => void;
}>((set) => ({
  view: sceneMode() === "station" ? "station" : "overview",
  setView: (view) => set({ view }),
  toggleView: (view) =>
    set((s) => ({ view: s.view === view ? "overview" : view })),
}));

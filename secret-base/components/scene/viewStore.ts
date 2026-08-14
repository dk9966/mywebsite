import { create } from "zustand";

export type ViewName = "overview" | "projects" | "about";

/** Which camera view the scene is in. Click an island to toggle its view. */
export const useViewStore = create<{
  view: ViewName;
  setView: (view: ViewName) => void;
  toggleView: (view: Exclude<ViewName, "overview">) => void;
}>((set) => ({
  view: "overview",
  setView: (view) => set({ view }),
  toggleView: (view) =>
    set((s) => ({ view: s.view === view ? "overview" : view })),
}));

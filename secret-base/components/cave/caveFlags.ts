const FLAGS = new URLSearchParams(typeof window === "undefined" ? "" : window.location.search);
/** Debug switches for side-by-side checks against the Blender render. */
export const CAVE_FLAGS = {
  /** The full mist ray-march (all ten volumes, ~48 lights): slow, opt-in. */
  haze: FLAGS.has("haze"),
  /** Spotlight beams and the cave-wide veil, the cheap stand-in for the haze. */
  beams: !FLAGS.has("haze") && !FLAGS.has("nobeams"),
  bloom: !FLAGS.has("nobloom"),
  voxels: !FLAGS.has("novoxels"),
  /** The section titles floating above the islands. */
  labels: !FLAGS.has("nolabels"),
  /** Show one surface input instead of the lit result: albedo, coverage, normal, roughness, metallic, specular, light. */
  debug: FLAGS.get("debug"),
  /** The white lights flicker on at load (`?nostartup`: on from the first frame). */
  startup: !FLAGS.has("nostartup"),
  /** Shadow maps for the live surface lights. */
  shadows: !FLAGS.has("noshadows"),
  /** Finer shadow maps round the platforms the camera zooms in on (`?nofocus` compares against the main maps alone). */
  focusShadows: !FLAGS.has("nofocus"),
  /** The camera stays on the Blender camera; `?free` brings back Blender-style navigation. */
  locked: !FLAGS.has("free"),
  /** The desk page's HUD panel wall above the central console. */
  panels: !FLAGS.has("nopanels"),
  /** Dev only: sliders for each platform's final zoomed-in camera (saved to zoomLayout.json). */
  editZoom: import.meta.env.DEV && !FLAGS.has("noedit") && !FLAGS.has("free"),
  /** Dev only: the panel wall's size slider (saved to panelLayout.json). */
  editPanels: import.meta.env.DEV && !FLAGS.has("noedit") && !FLAGS.has("nopanels"),
  /**
   * Dev only, `?editlabels`: drag the section titles to move them, scroll to
   * resize (saved to labelLayout.json). Off by default: a title click zooms to its platform.
   */
  editLabels: import.meta.env.DEV && FLAGS.has("editlabels"),
  /** Log-encoded scene-linear output instead of the view transform. */
  logOutput: FLAGS.has("logout"),
  /** Render every frame instead of on demand (profiling, comparisons). */
  continuous: FLAGS.has("continuous"),
  /** Voxelize server override, e.g. `?voxelServer=http://localhost:4101`. */
  voxelServer: FLAGS.get("voxelServer"),
};

const tune = (key: string, fallback: number) => (FLAGS.has(key) ? Number(FLAGS.get(key)) : fallback);

/**
 * Tuned against cave-web/reference (see cave-web/README.md). Each value can be
 * overridden from the URL (`/cave?hazeGain=1.2`) while comparing captures.
 */
export const CAVE_TUNING = {
  /** MSAA samples (0 = off; sub-pixel geometry then aliases into speckle). */
  msaa: tune("msaa", 4),
  hazeGain: tune("hazeGain", 1),
  hazeAmbient: tune("hazeAmbient", 0.05),
  /** Haze ray-march resolution as a fraction of the frame (1 = full). */
  hazeScale: tune("hazeScale", 0.35),
  /** Share of each mist's light budget the weakest lights may drop (0 = keep all that reach it). */
  hazeCull: tune("hazeCull", 0.03),
  bloom: {
    intensity: tune("bloomIntensity", 1.8),
    radius: tune("bloomRadius", 0.36),
    threshold: tune("bloomThreshold", 0.7),
    smoothing: tune("bloomSmoothing", 0.3),
  },
};

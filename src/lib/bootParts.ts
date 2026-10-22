// Canonical boot-sequence parts in playback order. Delays are ms from the
// panel's power-on (--boot-delay) unless scope is "global" (ms from mount).
//
// Timeline was authored at BOOT_BASE_TOTAL_MS and scaled to BOOT_TOTAL_MS so
// every delay/duration keeps the same relative spacing.

export const BOOT_BASE_TOTAL_MS = 3900;
export const BOOT_TOTAL_MS = 5000;
const BOOT_SCALE = BOOT_TOTAL_MS / BOOT_BASE_TOTAL_MS;

/** Scale a ms value from the 3.9s reference timeline to the live total. */
export function bootScaleMs(ms: number): number {
  return Math.round(ms * BOOT_SCALE);
}

export type BootPartId =
  | "edgeGlow"
  | "powerFlash"
  | "staticNoise"
  | "scanA"
  | "flickerFill"
  | "diagText"
  | "titleReveal"
  | "scanB"
  | "contentJitter"
  | "reticle"
  | "bezelDraw"
  | "bodyReveal"
  | "alignGrid"
  | "readoutBars"
  | "glassAssembly"
  | "scaffoldFade";

export type BootPartScope = "panel" | "global";

export type BootWebglRole = "glow" | "flicker" | "frame" | "assembly";

export interface BootPartDef {
  id: BootPartId;
  label: string;
  scope: BootPartScope;
  defaultDelayMs: number;
  defaultDurationMs: number;
  /** Shown at boot by default; defaults to true. */
  defaultVisible?: boolean;
  /** Timing sliders only — no visibility toggle in the panel. */
  hideCheckbox?: boolean;
  webgl?: BootWebglRole;
}

/** Ordered list — first row is earliest in the sequence. */
export const BOOT_PARTS: BootPartDef[] = [
  {
    id: "edgeGlow",
    label: "Edge glow",
    scope: "panel",
    defaultDelayMs: bootScaleMs(0),
    defaultDurationMs: bootScaleMs(320),
    webgl: "glow",
  },
  {
    id: "powerFlash",
    label: "Power flash",
    scope: "panel",
    defaultDelayMs: bootScaleMs(200),
    defaultDurationMs: bootScaleMs(560),
  },
  {
    id: "staticNoise",
    label: "Static noise",
    scope: "panel",
    defaultDelayMs: bootScaleMs(240),
    defaultDurationMs: bootScaleMs(640),
  },
  {
    id: "scanA",
    label: "Scan line A",
    scope: "panel",
    defaultDelayMs: bootScaleMs(300),
    defaultDurationMs: bootScaleMs(520),
  },
  {
    id: "flickerFill",
    label: "Power flicker",
    scope: "panel",
    defaultDelayMs: bootScaleMs(320),
    defaultDurationMs: bootScaleMs(500),
    webgl: "flicker",
  },
  {
    id: "diagText",
    label: "Diagnostic text",
    scope: "panel",
    defaultDelayMs: bootScaleMs(520),
    defaultDurationMs: bootScaleMs(180),
  },
  {
    id: "titleReveal",
    label: "Title reveal",
    scope: "panel",
    defaultDelayMs: bootScaleMs(720),
    defaultDurationMs: bootScaleMs(480),
  },
  {
    id: "scanB",
    label: "Scan line B",
    scope: "panel",
    defaultDelayMs: bootScaleMs(760),
    defaultDurationMs: bootScaleMs(430),
  },
  {
    id: "contentJitter",
    label: "Content jitter",
    scope: "panel",
    defaultDelayMs: bootScaleMs(780),
    defaultDurationMs: bootScaleMs(800),
  },
  {
    id: "reticle",
    label: "Calibration reticle",
    scope: "panel",
    defaultDelayMs: bootScaleMs(840),
    defaultDurationMs: bootScaleMs(700),
    defaultVisible: false,
    hideCheckbox: true,
  },
  {
    id: "bezelDraw",
    label: "Bezel draw-on",
    scope: "panel",
    defaultDelayMs: bootScaleMs(820),
    defaultDurationMs: bootScaleMs(530),
    webgl: "frame",
  },
  {
    id: "bodyReveal",
    label: "Body reveal",
    scope: "panel",
    defaultDelayMs: bootScaleMs(950),
    defaultDurationMs: bootScaleMs(620),
  },
  {
    id: "alignGrid",
    label: "Alignment grid",
    scope: "panel",
    defaultDelayMs: bootScaleMs(1000),
    defaultDurationMs: bootScaleMs(340),
  },
  {
    id: "readoutBars",
    label: "Readout bars",
    scope: "panel",
    defaultDelayMs: bootScaleMs(1150),
    defaultDurationMs: bootScaleMs(380),
    defaultVisible: false,
    hideCheckbox: true,
  },
  {
    id: "glassAssembly",
    label: "Glass fill ramp",
    scope: "panel",
    defaultDelayMs: bootScaleMs(1350),
    defaultDurationMs: bootScaleMs(1550),
    webgl: "assembly",
  },
  {
    id: "scaffoldFade",
    label: "Scaffold fade-out",
    scope: "global",
    defaultDelayMs: bootScaleMs(2900),
    defaultDurationMs: bootScaleMs(180),
  },
];

export type BootPanelId =
  | "profile"
  | "featured"
  | "experience"
  | "skills"
  | "education"
  | "contact";

export const BOOT_PANEL_LABELS: Record<BootPanelId, string> = {
  profile: "Profile",
  featured: "Projects",
  experience: "Experience",
  skills: "Skills",
  education: "Education",
  contact: "Contact",
};

export const DEFAULT_PANEL_START_MS: Record<BootPanelId, number> = {
  profile: bootScaleMs(550),
  featured: bootScaleMs(690),
  experience: bootScaleMs(830),
  skills: bootScaleMs(970),
  education: bootScaleMs(1110),
  contact: bootScaleMs(1240),
};

/** CSS custom property names for timing (set on :root). */
export function bootPartCssVars(
  parts: Record<BootPartId, { delayMs: number; durationMs: number }>,
): Record<string, string> {
  const out: Record<string, string> = {
    "--boot-diag-stagger": `${bootScaleMs(40)}ms`,
    "--boot-reticle-in-dur": `${bootScaleMs(200)}ms`,
    "--boot-reticle-arc-offset-mid": `${bootScaleMs(80)}ms`,
    "--boot-reticle-spin-dur": `${bootScaleMs(1400)}ms`,
    "--boot-reticle-arc-offset-inner": `${bootScaleMs(160)}ms`,
    "--boot-readout-stagger": `${bootScaleMs(55)}ms`,
  };
  for (const def of BOOT_PARTS) {
    const t = parts[def.id];
    out[`--boot-off-${def.id}`] = `${t.delayMs}ms`;
    out[`--boot-dur-${def.id}`] = `${t.durationMs}ms`;
  }
  return out;
}

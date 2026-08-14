import { create } from "zustand";
import {
  addSegmentToTopology,
  deleteSegmentInTopology,
  EMPTY_TOPOLOGY,
  joinVertexInTopology,
  nearestOnSegmentXZ,
  resolveSegmentGeom,
  resolveSegmentGeomById,
  setVertexInTopology,
  splitSegmentInTopology,
  type CircuitTopology,
  type SegmentAxis,
  type SegmentGeom,
} from "../lib/circuitTopology";
import type { GridPath, Vec3 } from "../lib/gridBuilder";
import {
  addMeshToEdits,
  DEFAULT_MESH_SIZE,
  deleteMeshInEdits,
  EMPTY_MESH_EDITS,
  rotateMeshInEdits,
  setMeshBoundsInEdits,
  type CircuitMesh,
  type CircuitMeshEdits,
  type MeshBounds,
  type MeshSize,
} from "../lib/circuitMeshes";
import type { MeshKind } from "../lib/circuitMeshBoxes";
import {
  DEFAULT_MERGE_EPS,
  snapAnglesToGrid,
} from "../lib/snapCircuitAngles";
import {
  DEFAULT_SCANNER_PARAMS,
  DEFAULT_TOP_VIEW_CAMERA,
  PUBLISHED_TUNING,
  type ScannerParams,
  type TopViewCamera,
} from "../lib/tronPathsFromCircuitsTraced";

/** Per-line tweaks layered on top of the automatic scan schedule. */
export interface PathOverride {
  spawnTime?: number;
  cursorSpeed?: number;
  offset?: Vec3;
  hidden?: boolean;
  /** Draw from end → start instead of start → end. */
  reversed?: boolean;
}

/** Whole-board placement applied before per-line offsets. */
export interface BoardTransform {
  offset: Vec3;
  rotationYDeg: number;
  scale: number;
}

/** Serializable snapshot of everything the tuner controls. */
export interface CircuitTuning {
  timing: ScannerParams;
  transform: BoardTransform;
  topViewCamera: TopViewCamera;
  overrides: Record<string, PathOverride>;
  topology: CircuitTopology;
  /** Component mesh placement/size edits for the 2D canvas editor. */
  meshEdits: CircuitMeshEdits;
  /** Max XZ distance Snap 45° uses when merging vertices and mesh joins. */
  snapMergeEps: number;
}

export const DEFAULT_TRANSFORM: BoardTransform = {
  offset: [0, 0, 0],
  rotationYDeg: 0,
  scale: 1,
};

/** Factory baseline if nothing is committed or persisted. */
const FACTORY_TUNING: CircuitTuning = {
  timing: { ...DEFAULT_SCANNER_PARAMS },
  transform: { ...DEFAULT_TRANSFORM },
  topViewCamera: {
    ...DEFAULT_TOP_VIEW_CAMERA,
    offset: [...DEFAULT_TOP_VIEW_CAMERA.offset] as Vec3,
  },
  overrides: {},
  topology: { ...EMPTY_TOPOLOGY },
  meshEdits: { ...EMPTY_MESH_EDITS },
  snapMergeEps: DEFAULT_MERGE_EPS,
};

const STORAGE_KEY = "circuit-tuning:v2";
const MAX_UNDO = 60;

/** Browser draft overlay; merged on load. Reset ignores this and uses committed JSON only. */
type StoredTuning = Partial<CircuitTuning> & { _draft?: boolean };

type EditSnapshot = {
  timing: ScannerParams;
  transform: BoardTransform;
  overrides: Record<string, PathOverride>;
  topology: CircuitTopology;
  meshEdits: CircuitMeshEdits;
  selectedLineIds: string[];
  selectedMeshIds: string[];
};

function snapshot(state: EditSnapshot): EditSnapshot {
  return {
    timing: { ...state.timing },
    transform: {
      ...state.transform,
      offset: [...state.transform.offset] as Vec3,
    },
    overrides: structuredClone(state.overrides),
    topology: structuredClone(state.topology),
    meshEdits: structuredClone(state.meshEdits),
    selectedLineIds: [...state.selectedLineIds],
    selectedMeshIds: [...state.selectedMeshIds],
  };
}

function commitBaseline(payload: CircuitTuning): void {
  runtimePublished = cloneTuning(payload);
}

function syncDraftToStorage(payload: CircuitTuning): void {
  if (typeof window === "undefined") return;
  try {
    const draft: StoredTuning = { ...payload, _draft: true };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Quota or private browsing — in-memory state still works this session.
  }
}

function loadPersisted(): CircuitTuning {
  const published = getPublishedBaseline();
  if (typeof window === "undefined") return cloneTuning(published);
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const legacy = window.localStorage.getItem("circuit-tuning:v1");
      if (legacy)
        return mergeTuning(JSON.parse(legacy) as Partial<CircuitTuning>);
      return cloneTuning(published);
    }
    const stored = JSON.parse(raw) as StoredTuning;
    if (stored._draft === true) {
      const { _draft: _, ...draft } = stored;
      return mergeTuning({ ...published, ...draft });
    }
    return cloneTuning(published);
  } catch {
    return cloneTuning(published);
  }
}

function cloneTuning(t: CircuitTuning): CircuitTuning {
  return {
    timing: { ...t.timing },
    transform: { ...t.transform, offset: [...t.transform.offset] as Vec3 },
    topViewCamera: {
      ...t.topViewCamera,
      offset: [...t.topViewCamera.offset] as Vec3,
    },
    overrides: structuredClone(t.overrides),
    topology: structuredClone(t.topology),
    meshEdits: structuredClone(t.meshEdits),
    snapMergeEps: t.snapMergeEps,
  };
}

/** Defensive merge so older/partial persisted blobs never break the store. */
function mergeTuning(input: Partial<CircuitTuning>): CircuitTuning {
  const base = cloneTuning(FACTORY_TUNING);
  return {
    timing: { ...base.timing, ...(input.timing ?? {}) },
    transform: {
      ...base.transform,
      ...(input.transform ?? {}),
      offset: (input.transform?.offset ?? base.transform.offset).slice(
        0,
        3,
      ) as Vec3,
    },
    topViewCamera: {
      ...base.topViewCamera,
      ...(input.topViewCamera ?? {}),
      offset: (input.topViewCamera?.offset ?? base.topViewCamera.offset).slice(
        0,
        3,
      ) as Vec3,
    },
    overrides: input.overrides ?? {},
    topology: input.topology
      ? structuredClone(input.topology)
      : { ...EMPTY_TOPOLOGY },
    meshEdits: input.meshEdits
      ? structuredClone(input.meshEdits)
      : { ...EMPTY_MESH_EDITS },
    snapMergeEps: input.snapMergeEps ?? base.snapMergeEps,
  };
}

/** Bundled src/data/circuits-tuning.json — the committed baseline after Save + reload. */
const PUBLISHED: CircuitTuning = mergeTuning(PUBLISHED_TUNING);

/** Last successful Save / Import this session; Reset uses this, not the localStorage draft. */
let runtimePublished: CircuitTuning | null = null;

function getPublishedBaseline(): CircuitTuning {
  return runtimePublished ?? PUBLISHED;
}

const SAVE_DEFAULT_ROUTE = "/__save-circuits-tuning";
const VERSIONS_ROUTE = "/__circuit-versions";

/**
 * Read the committed JSON straight off disk via the dev server. The bundled
 * `PUBLISHED` is only a snapshot from page-load, so a save in another tab/browser
 * isn't visible to it — fetching keeps Reset honest across sessions.
 */
async function fetchCommittedFromDisk(): Promise<CircuitTuning | null> {
  if (typeof window === "undefined") return null;
  try {
    const res = await fetch(SAVE_DEFAULT_ROUTE, {
      method: "GET",
      headers: { "Cache-Control": "no-store" },
    });
    if (!res.ok) return null;
    const json = (await res.json()) as Partial<CircuitTuning>;
    return mergeTuning(json);
  } catch {
    return null;
  }
}

async function fetchVersionFromDisk(name: string): Promise<CircuitTuning | null> {
  if (typeof window === "undefined") return null;
  try {
    const res = await fetch(
      `${VERSIONS_ROUTE}?name=${encodeURIComponent(name)}`,
      { headers: { "Cache-Control": "no-store" } },
    );
    if (!res.ok) return null;
    const json = (await res.json()) as Partial<CircuitTuning>;
    return mergeTuning(json);
  } catch {
    return null;
  }
}

function applyTuningBaseline(baseline: CircuitTuning): void {
  useCircuitTuning.setState({
    ...cloneTuning(baseline),
    selectedLineIds: [],
    selectedMeshIds: [],
    selectedVertex: null,
    editTool: "select",
    addLineStart: null,
    addMeshKind: null,
    addMeshSize: null,
    addMeshVariant: null,
    isDraggingVertex: false,
    undoStack: [],
    redoStack: [],
  });
}

const PASTE_OFFSET = 0.5;

let lineClipboard: SegmentGeom[] = [];
let pasteGeneration = 0;
let editPathsGetter: (() => GridPath[]) | null = null;

function isEditableLine(id: string): boolean {
  return id.startsWith("trace-") || id.startsWith("user-");
}

function getEditPaths(): GridPath[] {
  return editPathsGetter?.() ?? [];
}

/** Canvas editor registers its path resolver so copy can read baseline trace geometry. */
export function setEditPathsGetter(getter: (() => GridPath[]) | null): void {
  editPathsGetter = getter;
}

function tuningPayload(
  state: Pick<
    CircuitTuning,
    | "timing"
    | "transform"
    | "topViewCamera"
    | "overrides"
    | "topology"
    | "meshEdits"
    | "snapMergeEps"
  >,
): CircuitTuning {
  return {
    timing: state.timing,
    transform: state.transform,
    topViewCamera: state.topViewCamera,
    overrides: state.overrides,
    topology: state.topology,
    meshEdits: state.meshEdits,
    snapMergeEps: state.snapMergeEps,
  };
}

async function writeDefault(
  payload: CircuitTuning,
  opts: { downloadOnFailure?: boolean } = {},
): Promise<boolean> {
  const body = JSON.stringify(payload, null, 2);

  try {
    const res = await fetch(SAVE_DEFAULT_ROUTE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    if (!res.ok) throw new Error("save failed");
    commitBaseline(payload);
    syncDraftToStorage(payload);
    return true;
  } catch {
    if (opts.downloadOnFailure) {
      const blob = new Blob([`${body.trimEnd()}\n`], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "circuits-tuning.json";
      a.click();
      URL.revokeObjectURL(url);
    }
    return false;
  }
}

export type EditTool = "select" | "addLine" | "addMesh" | "split";

function vecTooClose(a: Vec3, b: Vec3): boolean {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]) < 0.05;
}

interface CircuitTuningStore extends CircuitTuning {
  selectedLineIds: string[];
  selectedMeshIds: string[];
  selectedVertex: 0 | 1 | null;
  editTool: EditTool;
  addLineStart: Vec3 | null;
  addMeshKind: MeshKind | null;
  addMeshSize: MeshSize | null;
  /** Catalog variant id pending placement (null for a plain box). */
  addMeshVariant: string | null;
  isDraggingVertex: boolean;
  undoStack: EditSnapshot[];
  redoStack: EditSnapshot[];
  /** Lines currently on the clipboard (0 when empty). */
  clipboardLineCount: number;

  select: (id: string | null) => void;
  selectMesh: (id: string | null) => void;
  setBoxSelection: (lineIds: string[], meshIds: string[]) => void;
  clearSelection: () => void;
  selectVertex: (end: 0 | 1 | null) => void;
  setEditTool: (tool: EditTool) => void;
  startAddMesh: (kind: MeshKind, size?: MeshSize, variant?: string | null) => void;
  setAddLineStart: (point: Vec3 | null) => void;
  setDraggingVertex: (dragging: boolean) => void;
  pushUndo: () => void;
  undo: () => void;
  redo: () => void;

  setTiming: (patch: Partial<ScannerParams>) => void;
  setTransform: (patch: Partial<BoardTransform>) => void;
  setTopViewCamera: (patch: Partial<TopViewCamera>) => void;
  setSnapMergeEps: (value: number) => void;
  setOverride: (id: string, patch: Partial<PathOverride>) => void;
  clearOverride: (id: string) => void;
  bakeFromBaseline: (
    baseline: Record<string, { spawnTime: number; cursorSpeed: number }>,
  ) => void;

  moveVertex: (
    segmentId: string,
    end: 0 | 1,
    point: Vec3,
    paths: GridPath[],
    baseGeom: { start: Vec3; end: Vec3 },
    commit: boolean,
    axis?: SegmentAxis,
  ) => void;
  setVertices: (
    updates: Array<{
      segmentId: string;
      end: 0 | 1;
      point: Vec3;
      baseGeom: { start: Vec3; end: Vec3 };
    }>,
  ) => void;
  /** Replace geometry for multiple segments at once (group move/scale). */
  setLineGeometries: (geoms: Record<string, SegmentGeom>) => void;
  /** Replace bounds for multiple meshes at once (group move/scale). */
  setMeshBoundsMap: (bounds: Record<string, MeshBounds>) => void;
  deleteSelectedSegment: () => void;
  deleteSelectedMesh: () => void;
  deleteSelection: () => void;
  /** Split a segment at the point on it nearest the given world point. */
  splitSegmentAtPoint: (
    paths: GridPath[],
    segmentId: string,
    point: Vec3,
  ) => boolean;
  /** Snap every line to its nearest 45° step, keeping junctions intact. */
  snapAnglesToGrid: (
    paths: GridPath[],
    meshes?: CircuitMesh[],
  ) => { changed: number; merged: number; collapsed: number; meshSnapped: number };
  addLineSegment: (start: Vec3, end: Vec3) => void;
  setMeshBounds: (id: string, bounds: MeshBounds) => void;
  addMeshAt: (kind: MeshKind, cx: number, cz: number) => void;
  /** Rotate each selected mesh +90° about its center (AABB swap + yaw). */
  rotateSelectedMeshes: (resolvedMeshes: CircuitMesh[]) => boolean;
  cancelEditTool: () => void;
  copySelectedLines: () => boolean;
  pasteLines: () => boolean;

  resetAll: () => Promise<void>;
  /** Revert to the named version file on disk (dev server). */
  resetToVersion: (name: string) => Promise<boolean>;
  exportJSON: () => string;
  importJSON: (text: string) => boolean;
  /** Write current tuning to src/data/circuits-tuning.json (dev) or download fallback. */
  saveAsDefault: () => Promise<boolean>;
}

export const useCircuitTuning = create<CircuitTuningStore>((set, get) => {
  const initial = loadPersisted();
  return {
    ...initial,
    selectedLineIds: [],
    selectedMeshIds: [],
    selectedVertex: null,
    editTool: "select",
    addLineStart: null,
    addMeshKind: null,
    addMeshSize: null,
    addMeshVariant: null,
    isDraggingVertex: false,
    undoStack: [],
    redoStack: [],
    clipboardLineCount: 0,

    select: (id) =>
      set({
        selectedLineIds: id ? [id] : [],
        selectedMeshIds: [],
        selectedVertex: null,
      }),

    selectMesh: (id) =>
      set({
        selectedMeshIds: id ? [id] : [],
        selectedLineIds: [],
        selectedVertex: null,
      }),

    setBoxSelection: (lineIds, meshIds) =>
      set({
        selectedLineIds: lineIds,
        selectedMeshIds: meshIds,
        selectedVertex: null,
      }),

    clearSelection: () =>
      set({ selectedLineIds: [], selectedMeshIds: [], selectedVertex: null }),

    selectVertex: (end) => set({ selectedVertex: end }),

    setEditTool: (tool) =>
      set({
        editTool: tool,
        addLineStart: null,
        addMeshKind: tool === "addMesh" ? get().addMeshKind : null,
        addMeshSize: tool === "addMesh" ? get().addMeshSize : null,
        addMeshVariant: tool === "addMesh" ? get().addMeshVariant : null,
        // Split acts on the already-selected line, so keep it selected when
        // entering the tool; every other tool starts from a clean slate.
        selectedLineIds: tool === "split" ? get().selectedLineIds : [],
        selectedVertex: null,
        selectedMeshIds: [],
      }),

    startAddMesh: (kind, size, variant = null) => {
      const s = get();
      if (
        s.editTool === "addMesh" &&
        s.addMeshKind === kind &&
        s.addMeshVariant === variant
      ) {
        const nextSize = size ?? DEFAULT_MESH_SIZE[kind];
        const sameSize =
          s.addMeshSize != null &&
          s.addMeshSize.w === nextSize.w &&
          s.addMeshSize.h === nextSize.h;
        if (sameSize) {
          set({
            editTool: "select",
            addMeshKind: null,
            addMeshSize: null,
            addMeshVariant: null,
            addLineStart: null,
            selectedVertex: null,
          });
          return;
        }
      }
      set({
        editTool: "addMesh",
        addMeshKind: kind,
        addMeshSize: size ?? DEFAULT_MESH_SIZE[kind],
        addMeshVariant: variant,
        addLineStart: null,
        selectedLineIds: [],
        selectedVertex: null,
        selectedMeshIds: [],
      });
    },

    setAddLineStart: (point) => set({ addLineStart: point }),

    setDraggingVertex: (dragging) => set({ isDraggingVertex: dragging }),

    cancelEditTool: () =>
      set({
        editTool: "select",
        addLineStart: null,
        addMeshKind: null,
        addMeshSize: null,
        addMeshVariant: null,
      }),

    copySelectedLines: () => {
      const { selectedLineIds, topology } = get();
      const editable = selectedLineIds.filter(isEditableLine);
      if (editable.length === 0) return false;

      const paths = getEditPaths();
      const entries: SegmentGeom[] = [];
      for (const id of editable) {
        const geom = resolveSegmentGeomById(id, paths, topology);
        if (!geom) continue;
        entries.push({
          start: [...geom.start] as Vec3,
          end: [...geom.end] as Vec3,
        });
      }
      if (entries.length === 0) return false;
      lineClipboard = entries;
      pasteGeneration = 0;
      set({ clipboardLineCount: entries.length });
      return true;
    },

    pasteLines: () => {
      if (lineClipboard.length === 0) return false;
      get().pushUndo();
      pasteGeneration += 1;
      const offset = PASTE_OFFSET * pasteGeneration;
      let topology = get().topology;
      const newIds: string[] = [];
      for (const geom of lineClipboard) {
        const start: Vec3 = [
          geom.start[0] + offset,
          geom.start[1],
          geom.start[2] + offset,
        ];
        const end: Vec3 = [
          geom.end[0] + offset,
          geom.end[1],
          geom.end[2] + offset,
        ];
        const result = addSegmentToTopology(topology, start, end);
        topology = result.topology;
        newIds.push(result.id);
      }
      set({
        topology,
        selectedLineIds: newIds,
        selectedMeshIds: [],
        selectedVertex: null,
      });
      return true;
    },

    pushUndo: () =>
      set((s) => ({
        undoStack: [...s.undoStack.slice(-(MAX_UNDO - 1)), snapshot(s)],
        redoStack: [],
      })),

    undo: () =>
      set((s) => {
        if (s.undoStack.length === 0) return s;
        const prev = s.undoStack[s.undoStack.length - 1];
        const current = snapshot(s);
        return {
          ...prev,
          undoStack: s.undoStack.slice(0, -1),
          redoStack: [...s.redoStack, current],
        };
      }),

    redo: () =>
      set((s) => {
        if (s.redoStack.length === 0) return s;
        const next = s.redoStack[s.redoStack.length - 1];
        const current = snapshot(s);
        return {
          ...next,
          undoStack: [...s.undoStack, current],
          redoStack: s.redoStack.slice(0, -1),
        };
      }),

    setTiming: (patch) => set((s) => ({ timing: { ...s.timing, ...patch } })),

    setTransform: (patch) =>
      set((s) => ({ transform: { ...s.transform, ...patch } })),

    setTopViewCamera: (patch) =>
      set((s) => ({
        topViewCamera: {
          ...s.topViewCamera,
          ...patch,
          offset: patch.offset
            ? ([...patch.offset] as Vec3)
            : s.topViewCamera.offset,
        },
      })),

    setSnapMergeEps: (value) => set({ snapMergeEps: value }),

    setOverride: (id, patch) =>
      set((s) => ({
        overrides: {
          ...s.overrides,
          [id]: { ...s.overrides[id], ...patch },
        },
      })),

    clearOverride: (id) =>
      set((s) => {
        const next = { ...s.overrides };
        delete next[id];
        return { overrides: next };
      }),

    bakeFromBaseline: (baseline) =>
      set((s) => {
        const next = { ...s.overrides };
        for (const [id, base] of Object.entries(baseline)) {
          next[id] = {
            ...next[id],
            spawnTime: next[id]?.spawnTime ?? base.spawnTime,
            cursorSpeed: next[id]?.cursorSpeed ?? base.cursorSpeed,
          };
        }
        return { overrides: next };
      }),

    moveVertex: (segmentId, end, point, paths, baseGeom, commit, axis) => {
      set((s) => {
        const topology = commit
          ? joinVertexInTopology(segmentId, end, point, paths, s.topology, axis)
          : setVertexInTopology(s.topology, segmentId, end, point, baseGeom);
        return { topology };
      });
    },

    setVertices: (updates) =>
      set((s) => {
        let topology = s.topology;
        for (const u of updates) {
          topology = setVertexInTopology(
            topology,
            u.segmentId,
            u.end,
            u.point,
            u.baseGeom,
          );
        }
        return { topology };
      }),

    setLineGeometries: (geoms) =>
      set((s) => ({
        topology: {
          ...s.topology,
          geometry: { ...s.topology.geometry, ...geoms },
        },
      })),

    setMeshBoundsMap: (boundsMap) =>
      set((s) => {
        const geometry = { ...s.meshEdits.geometry };
        for (const [id, bounds] of Object.entries(boundsMap)) {
          geometry[id] = { ...geometry[id], ...bounds };
        }
        return { meshEdits: { ...s.meshEdits, geometry } };
      }),

    deleteSelectedSegment: () => {
      const { selectedLineIds, topology } = get();
      if (selectedLineIds.length === 0) return;
      get().pushUndo();
      let next = topology;
      for (const id of selectedLineIds) {
        if (!next.deleted.includes(id)) next = deleteSegmentInTopology(next, id);
      }
      set({ topology: next, selectedLineIds: [], selectedVertex: null });
    },

    deleteSelectedMesh: () => {
      const { selectedMeshIds, meshEdits } = get();
      if (selectedMeshIds.length === 0) return;
      get().pushUndo();
      let next = meshEdits;
      for (const id of selectedMeshIds) {
        next = deleteMeshInEdits(next, id);
      }
      set({ meshEdits: next, selectedMeshIds: [] });
    },

    deleteSelection: () => {
      const { selectedLineIds, selectedMeshIds, topology, meshEdits } = get();
      if (selectedLineIds.length === 0 && selectedMeshIds.length === 0) return;
      get().pushUndo();
      let nextTopology = topology;
      for (const id of selectedLineIds) {
        if (!nextTopology.deleted.includes(id)) {
          nextTopology = deleteSegmentInTopology(nextTopology, id);
        }
      }
      let nextMeshEdits = meshEdits;
      for (const id of selectedMeshIds) {
        nextMeshEdits = deleteMeshInEdits(nextMeshEdits, id);
      }
      set({
        topology: nextTopology,
        meshEdits: nextMeshEdits,
        selectedLineIds: [],
        selectedMeshIds: [],
        selectedVertex: null,
      });
    },

    splitSegmentAtPoint: (paths, segmentId, point) => {
      const { topology } = get();
      const seg = paths.find((p) => p.id === segmentId);
      if (!seg) return false;
      const geom = resolveSegmentGeom(seg, topology);
      if (!geom) return false;
      const hit = nearestOnSegmentXZ(point, geom.start, geom.end);
      // Ignore clicks at the very ends; there's nothing to split off there.
      if (hit.t <= 0.02 || hit.t >= 0.98) return false;
      get().pushUndo();
      const next = splitSegmentInTopology(seg, hit.point, topology);
      set({
        topology: next,
        selectedLineIds: [],
        selectedVertex: null,
        editTool: "select",
      });
      return true;
    },

    snapAnglesToGrid: (paths, meshes) => {
      const { topology, changed, merged, collapsed, meshSnapped } = snapAnglesToGrid(
        paths,
        get().topology,
        { meshes, mergeEps: get().snapMergeEps },
      );
      if (changed === 0 && merged === 0 && collapsed === 0 && meshSnapped === 0) {
        return { changed: 0, merged: 0, collapsed: 0, meshSnapped: 0 };
      }
      get().pushUndo();
      set({ topology });
      return { changed, merged, collapsed, meshSnapped };
    },

    addLineSegment: (start, end) => {
      if (vecTooClose(start, end)) return;
      const { topology: next, id } = addSegmentToTopology(
        get().topology,
        start,
        end,
      );
      set({
        topology: next,
        selectedLineIds: [id],
        addLineStart: end,
        addMeshKind: null,
        addMeshSize: null,
        addMeshVariant: null,
        selectedVertex: null,
        selectedMeshIds: [],
      });
    },

    setMeshBounds: (id, bounds) =>
      set((s) => ({
        meshEdits: setMeshBoundsInEdits(s.meshEdits, id, bounds),
      })),

    rotateSelectedMeshes: (resolvedMeshes) => {
      const { selectedMeshIds, meshEdits } = get();
      if (selectedMeshIds.length === 0) return false;
      const byId = new Map(resolvedMeshes.map((m) => [m.id, m]));
      let next = meshEdits;
      let changed = false;
      for (const id of selectedMeshIds) {
        const mesh = byId.get(id);
        if (!mesh) continue;
        next = rotateMeshInEdits(next, mesh);
        changed = true;
      }
      if (!changed) return false;
      get().pushUndo();
      set({ meshEdits: next });
      return true;
    },

    addMeshAt: (kind, cx, cz) => {
      const size = get().addMeshSize ?? DEFAULT_MESH_SIZE[kind];
      const variant = get().addMeshVariant ?? undefined;
      const { edits, mesh } = addMeshToEdits(
        get().meshEdits,
        kind,
        cx,
        cz,
        size,
        variant,
      );
      set({
        meshEdits: edits,
        selectedMeshIds: [mesh.id],
        editTool: "select",
        addMeshKind: null,
        addMeshSize: null,
        addMeshVariant: null,
        selectedLineIds: [],
        selectedVertex: null,
      });
    },

    resetAll: async () => {
      // Prefer the live file on disk (reflects saves from any tab/browser);
      // fall back to this session's committed baseline if the dev route is down.
      const fromDisk = await fetchCommittedFromDisk();
      if (fromDisk) commitBaseline(fromDisk);
      applyTuningBaseline(fromDisk ?? getPublishedBaseline());
    },

    resetToVersion: async (name) => {
      const fromDisk = await fetchVersionFromDisk(name);
      if (!fromDisk) return false;
      applyTuningBaseline(fromDisk);
      return true;
    },

    exportJSON: () => {
      const {
        timing,
        transform,
        topViewCamera,
        overrides,
        topology,
        meshEdits,
        snapMergeEps,
      } = get();
      return JSON.stringify(
        {
          timing,
          transform,
          topViewCamera,
          overrides,
          topology,
          meshEdits,
          snapMergeEps,
        },
        null,
        2,
      );
    },

    importJSON: (text) => {
      try {
        const merged = mergeTuning(JSON.parse(text) as Partial<CircuitTuning>);
        set({
          ...merged,
          selectedLineIds: [],
          selectedMeshIds: [],
          selectedVertex: null,
          editTool: "select",
          addLineStart: null,
          addMeshKind: null,
          addMeshSize: null,
          addMeshVariant: null,
          undoStack: [],
          redoStack: [],
        });
        return true;
      } catch {
        return false;
      }
    },

    saveAsDefault: async () => {
      const payload = tuningPayload(get());
      return writeDefault(payload, { downloadOnFailure: true });
    },
  };
});

/** Default editor version — stored as src/data/circuit-versions/0.json. */
export const DEFAULT_CIRCUIT_VERSION = "0";

/**
 * Named version snapshots, each a JSON file the dev server serves from
 * src/data/circuit-versions (including version 0). Save / Reset in the 3D
 * editor use the active version file, not circuits-tuning.json.
 * Only works while the dev server is running.
 */
function versionUrl(name: string): string {
  return `${VERSIONS_ROUTE}?name=${encodeURIComponent(name)}`;
}

export function emptyVersionJSON(
  lineIds: string[],
  meshIds: string[],
): string {
  return JSON.stringify(
    {
      topology: {
        geometry: {},
        deleted: lineIds,
        added: [],
      },
      meshEdits: {
        geometry: {},
        deleted: meshIds,
        added: [],
      },
    },
    null,
    2,
  );
}

export async function listVersions(): Promise<string[]> {
  if (typeof window === "undefined") return [];
  try {
    const res = await fetch(VERSIONS_ROUTE, {
      headers: { "Cache-Control": "no-store" },
    });
    if (!res.ok) return [];
    const json = (await res.json()) as { versions?: string[] };
    return json.versions ?? [];
  } catch {
    return [];
  }
}

/** Write the current tuning to the named version file (creating it if needed). */
export async function saveVersion(name: string): Promise<boolean> {
  const body = JSON.stringify(tuningPayload(useCircuitTuning.getState()), null, 2);
  try {
    const res = await fetch(versionUrl(name), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** Save the editor state to a version file under circuit-versions/. */
export async function saveToVersion(name: string): Promise<boolean> {
  return saveVersion(name);
}

/** Create a new version file with an empty board (no baseline lines or meshes). */
export async function createBlankVersion(
  name: string,
  body: string,
): Promise<boolean> {
  try {
    const res = await fetch(versionUrl(name), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** Load a named version into the editor, replacing current tuning. */
export async function loadVersion(name: string): Promise<boolean> {
  try {
    const res = await fetch(versionUrl(name), {
      headers: { "Cache-Control": "no-store" },
    });
    if (!res.ok) return false;
    return useCircuitTuning.getState().importJSON(await res.text());
  } catch {
    return false;
  }
}

export async function deleteVersion(name: string): Promise<boolean> {
  try {
    const res = await fetch(versionUrl(name), { method: "DELETE" });
    return res.ok;
  } catch {
    return false;
  }
}

if (typeof window !== "undefined") {
  const persistDraft = () => {
    try {
      const state = useCircuitTuning.getState();
      const payload: StoredTuning = {
        timing: state.timing,
        transform: state.transform,
        topViewCamera: state.topViewCamera,
        overrides: state.overrides,
        topology: state.topology,
        meshEdits: state.meshEdits,
        snapMergeEps: state.snapMergeEps,
        _draft: true,
      };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch {
      // Ignore quota/serialization failures; tuning still works in-session.
    }
  };

  // Every edit fires this subscription — including each pointermove of a vertex
  // drag or group move. Serializing the whole board (tens of KB) and writing it
  // synchronously to localStorage that often stalled the main thread. Coalesce
  // into a single write once edits settle, and flush on page hide so the latest
  // draft is never lost.
  const PERSIST_DEBOUNCE_MS = 400;
  let persistTimer: number | undefined;
  const schedulePersist = () => {
    if (persistTimer !== undefined) window.clearTimeout(persistTimer);
    persistTimer = window.setTimeout(() => {
      persistTimer = undefined;
      persistDraft();
    }, PERSIST_DEBOUNCE_MS);
  };

  useCircuitTuning.subscribe(schedulePersist);

  window.addEventListener("pagehide", () => {
    if (persistTimer === undefined) return;
    window.clearTimeout(persistTimer);
    persistTimer = undefined;
    persistDraft();
  });
}

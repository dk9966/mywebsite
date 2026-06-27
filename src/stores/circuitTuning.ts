import { create } from "zustand";
import {
  addSegmentToTopology,
  deleteSegmentInTopology,
  EMPTY_TOPOLOGY,
  joinVertexInTopology,
  midpoint,
  resolveSegmentGeom,
  setVertexInTopology,
  splitSegmentInTopology,
  type CircuitTopology,
  type SegmentAxis,
  type SegmentGeom,
} from "../lib/circuitTopology";
import type { GridPath, Vec3 } from "../lib/gridBuilder";
import {
  addMeshToEdits,
  deleteMeshInEdits,
  EMPTY_MESH_EDITS,
  setMeshBoundsInEdits,
  type CircuitMesh,
  type CircuitMeshEdits,
  type MeshBounds,
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

/** Browser draft overlay; absent/false means load committed src/data/circuits-tuning.json. */
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

function persistCommitted(payload: CircuitTuning): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Ignore quota failures; JSON file is still the source of truth.
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

/** The committed tuning, normalized over the factory baseline. */
const PUBLISHED: CircuitTuning = mergeTuning(PUBLISHED_TUNING);

/** Updated when "Save as default" succeeds (dev write or manual import). */
let runtimePublished: CircuitTuning | null = null;

function getPublishedBaseline(): CircuitTuning {
  return runtimePublished ?? PUBLISHED;
}

const SAVE_DEFAULT_ROUTE = "/__save-circuits-tuning";

const PASTE_OFFSET = 0.5;

let lineClipboard: SegmentGeom[] = [];
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
    runtimePublished = cloneTuning(payload);
    persistCommitted(payload);
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

export type EditTool = "select" | "addLine" | "addMesh";

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
  isDraggingVertex: boolean;
  undoStack: EditSnapshot[];
  redoStack: EditSnapshot[];

  select: (id: string | null) => void;
  selectMesh: (id: string | null) => void;
  setBoxSelection: (lineIds: string[], meshIds: string[]) => void;
  clearSelection: () => void;
  selectVertex: (end: 0 | 1 | null) => void;
  setEditTool: (tool: EditTool) => void;
  startAddMesh: (kind: MeshKind) => void;
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
  splitSelectedSegment: (paths: GridPath[]) => void;
  /** Snap every line to its nearest 45° step, keeping junctions intact. */
  snapAnglesToGrid: (
    paths: GridPath[],
    meshes?: CircuitMesh[],
  ) => { changed: number; merged: number; meshSnapped: number };
  addLineSegment: (start: Vec3, end: Vec3) => void;
  setMeshBounds: (id: string, bounds: MeshBounds) => void;
  addMeshAt: (kind: MeshKind, cx: number, cz: number) => void;
  cancelEditTool: () => void;
  copySelectedLines: () => boolean;
  pasteLines: () => boolean;

  resetAll: () => void;
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
    isDraggingVertex: false,
    undoStack: [],
    redoStack: [],

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
        selectedLineIds: [],
        selectedVertex: null,
        selectedMeshIds: [],
      }),

    startAddMesh: (kind) =>
      set({
        editTool: "addMesh",
        addMeshKind: kind,
        addLineStart: null,
        selectedLineIds: [],
        selectedVertex: null,
        selectedMeshIds: [],
      }),

    setAddLineStart: (point) => set({ addLineStart: point }),

    setDraggingVertex: (dragging) => set({ isDraggingVertex: dragging }),

    cancelEditTool: () =>
      set({ editTool: "select", addLineStart: null, addMeshKind: null }),

    copySelectedLines: () => {
      const { selectedLineIds, topology } = get();
      const editable = selectedLineIds.filter(isEditableLine);
      if (editable.length === 0) return false;

      const paths = getEditPaths();
      const entries: SegmentGeom[] = [];
      for (const id of editable) {
        const seg = paths.find((p) => p.id === id);
        if (!seg) continue;
        const geom = resolveSegmentGeom(seg, topology);
        if (!geom) continue;
        entries.push({
          start: [...geom.start] as Vec3,
          end: [...geom.end] as Vec3,
        });
      }
      if (entries.length === 0) return false;
      lineClipboard = entries;
      return true;
    },

    pasteLines: () => {
      if (lineClipboard.length === 0) return false;
      get().pushUndo();
      let topology = get().topology;
      const newIds: string[] = [];
      for (const geom of lineClipboard) {
        const start: Vec3 = [
          geom.start[0] + PASTE_OFFSET,
          geom.start[1],
          geom.start[2] + PASTE_OFFSET,
        ];
        const end: Vec3 = [
          geom.end[0] + PASTE_OFFSET,
          geom.end[1],
          geom.end[2] + PASTE_OFFSET,
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

    splitSelectedSegment: (paths) => {
      const { selectedLineIds, topology } = get();
      if (selectedLineIds.length !== 1) return;
      const selectedId = selectedLineIds[0];
      const seg = paths.find((p) => p.id === selectedId);
      if (!seg) return;
      const geom = resolveSegmentGeom(seg, topology);
      if (!geom) return;
      get().pushUndo();
      const splitPoint = midpoint(geom.start, geom.end);
      const next = splitSegmentInTopology(seg, splitPoint, topology);
      set({ topology: next, selectedLineIds: [], selectedVertex: null });
    },

    snapAnglesToGrid: (paths, meshes) => {
      const { topology, changed, merged, meshSnapped } = snapAnglesToGrid(
        paths,
        get().topology,
        { meshes, mergeEps: get().snapMergeEps },
      );
      if (changed === 0 && merged === 0 && meshSnapped === 0) {
        return { changed: 0, merged: 0, meshSnapped: 0 };
      }
      get().pushUndo();
      set({ topology });
      return { changed, merged, meshSnapped };
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
        addLineStart: null,
        addMeshKind: null,
        selectedVertex: null,
        selectedMeshIds: [],
      });
    },

    setMeshBounds: (id, bounds) =>
      set((s) => ({
        meshEdits: setMeshBoundsInEdits(s.meshEdits, id, bounds),
      })),

    addMeshAt: (kind, cx, cz) => {
      const { edits, mesh } = addMeshToEdits(get().meshEdits, kind, cx, cz);
      set({
        meshEdits: edits,
        selectedMeshIds: [mesh.id],
        editTool: "select",
        addMeshKind: null,
        selectedLineIds: [],
        selectedVertex: null,
      });
    },

    resetAll: () =>
      set({
        ...cloneTuning(getPublishedBaseline()),
        selectedLineIds: [],
        selectedMeshIds: [],
        selectedVertex: null,
        editTool: "select",
        addLineStart: null,
        addMeshKind: null,
        isDraggingVertex: false,
        undoStack: [],
        redoStack: [],
      }),

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
        runtimePublished = cloneTuning(merged);
        persistCommitted(merged);
        set({
          ...merged,
          selectedLineIds: [],
          selectedMeshIds: [],
          selectedVertex: null,
          editTool: "select",
          addLineStart: null,
          addMeshKind: null,
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

if (typeof window !== "undefined") {
  useCircuitTuning.subscribe((state) => {
    try {
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
  });
}

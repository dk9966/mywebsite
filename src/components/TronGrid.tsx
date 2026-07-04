import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { Line2 } from "three/addons/lines/Line2.js";
import { LineGeometry } from "three/addons/lines/LineGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { GRID_EXTENT } from "../lib/constants";
import {
  buildScene,
  sceneDuration,
  totalPathLength,
  type GridPath,
  type Vec3,
} from "../lib/gridBuilder";
import { useClock } from "../stores/clock";
import { useLineConfig, type LineConfig } from "../stores/lineConfig";

const sharedTipGeo = new THREE.SphereGeometry(0.5, 8, 6);
const _xAxis = new THREE.Vector3(1, 0, 0);
const _dir = new THREE.Vector3();
const _lineDisplayColor = new THREE.Color();
const _tipDisplayColor = new THREE.Color();

function lineDisplayColor(cfg: LineConfig, out = _lineDisplayColor): THREE.Color {
  return out.set(cfg.lineColor).multiplyScalar(cfg.lineEmission);
}

function pathLineDisplayColor(
  pathLineColor: string | undefined,
  cfg: LineConfig,
  out = _lineDisplayColor,
): THREE.Color {
  if (pathLineColor) {
    return out.set(pathLineColor).multiplyScalar(cfg.lineEmission);
  }
  return lineDisplayColor(cfg, out);
}

function pathTipDisplayColor(
  pathLineColor: string | undefined,
  cfg: LineConfig,
  out = _tipDisplayColor,
): THREE.Color {
  if (pathLineColor) {
    return out.set(pathLineColor).multiplyScalar(cfg.lineEmission * 1.35);
  }
  return out.set(cfg.tipColor);
}

function lineColorDirty(next: LineConfig, prev: LineConfig): boolean {
  return next.lineColor !== prev.lineColor || next.lineEmission !== prev.lineEmission;
}

type AnimatedLine = {
  spawnTime: number;
  pathLength: number;
  cursorSpeed: number;
  waypoints: Vec3[];
  line: Line2;
  lineGeo: LineGeometry;
  tip: THREE.Mesh;
  pointCount: number;
  cumDist: Float32Array;
  positions: Float32Array;
  colorsVert: Float32Array;
  lastLeadSlot: number;
  savedLinePos: [number, number, number];
  pathLineColor?: string;
};

let sharedFatLineMaterial: LineMaterial | null = null;
let sharedScreenLineMaterial: LineMaterial | null = null;

function getSharedFatLineMaterial(): LineMaterial {
  sharedFatLineMaterial ??= new LineMaterial({
    color: 0xffffff,
    // World-space thickness — screen-pixel width was invisible under bloom.
    linewidth: 0.04,
    worldUnits: true,
    dashed: false,
    vertexColors: true,
    transparent: true,
    toneMapped: false,
    depthWrite: false,
  });
  return sharedFatLineMaterial;
}

function getScreenLineMaterial(): LineMaterial {
  sharedScreenLineMaterial ??= new LineMaterial({
    color: 0xffffff,
    linewidth: 2.5,
    worldUnits: false,
    dashed: false,
    vertexColors: true,
    transparent: true,
    toneMapped: false,
    depthWrite: false,
  });
  return sharedScreenLineMaterial;
}

function applyFatLineSharedStyle(cfg: LineConfig): void {
  const m = getSharedFatLineMaterial();
  m.linewidth = cfg.lineWidth;
  m.transparent = cfg.lineOpacity < 1;
  m.opacity = cfg.lineOpacity;
}

function applyScreenLineStyle(
  cfg: LineConfig,
  size: THREE.Vector2,
  screenWidth: number,
): void {
  const m = getScreenLineMaterial();
  m.linewidth = screenWidth;
  m.resolution.copy(size);
  m.transparent = cfg.lineOpacity < 1;
  m.opacity = cfg.lineOpacity;
}

/** Copies contiguous vertex buffers into fat-line segment instance pairs. */
function syncLineSegmentBuffers(
  geo: LineGeometry,
  positions: Float32Array,
  colorsVert: Float32Array,
  segmentCount: number,
): void {
  if (segmentCount <= 0) return;

  const iStart = geo.attributes
    .instanceStart as THREE.InterleavedBufferAttribute;
  const colStart = geo.attributes
    .instanceColorStart as THREE.InterleavedBufferAttribute;
  if (!iStart?.data?.array || !colStart?.data?.array) return;

  const posPairs = iStart.data.array as Float32Array;
  const colPairs = colStart.data.array as Float32Array;

  for (let i = 0; i < segmentCount; i++) {
    const o = i * 6;
    const vi = i * 3;

    posPairs[o] = positions[vi];
    posPairs[o + 1] = positions[vi + 1];
    posPairs[o + 2] = positions[vi + 2];
    posPairs[o + 3] = positions[vi + 3];
    posPairs[o + 4] = positions[vi + 4];
    posPairs[o + 5] = positions[vi + 5];

    colPairs[o] = colorsVert[vi];
    colPairs[o + 1] = colorsVert[vi + 1];
    colPairs[o + 2] = colorsVert[vi + 2];
    colPairs[o + 3] = colorsVert[vi + 3];
    colPairs[o + 4] = colorsVert[vi + 4];
    colPairs[o + 5] = colorsVert[vi + 5];
  }

  iStart.needsUpdate = true;
  geo.attributes.instanceEnd!.needsUpdate = true;
  colStart.needsUpdate = true;
  geo.attributes.instanceColorEnd!.needsUpdate = true;
}

function waypointsToPoints(
  waypoints: Vec3[],
  gridSpacing: number,
): THREE.Vector3[] {
  const out: THREE.Vector3[] = [];
  for (let i = 0; i < waypoints.length; i++) {
    const [x, y, z] = waypoints[i];
    if (i === 0) {
      out.push(new THREE.Vector3(x, y, z));
      continue;
    }
    const [px, py, pz] = waypoints[i - 1];
    const dx = x - px;
    const dy = y - py;
    const dz = z - pz;
    const maxDelta = Math.max(Math.abs(dx), Math.abs(dy), Math.abs(dz));
    const steps = Math.max(1, Math.round(maxDelta / gridSpacing));
    for (let s = 1; s <= steps; s++) {
      out.push(
        new THREE.Vector3(
          px + (dx * s) / steps,
          py + (dy * s) / steps,
          pz + (dz * s) / steps,
        ),
      );
    }
  }
  return out;
}

function computeCumDist(pts: THREE.Vector3[]): Float32Array {
  const cd = new Float32Array(pts.length);
  for (let i = 1; i < pts.length; i++) {
    cd[i] = cd[i - 1] + pts[i].distanceTo(pts[i - 1]);
  }
  return cd;
}

function fillBodyColor(
  arr: Float32Array,
  pointCount: number,
  color: THREE.Color,
) {
  for (let i = 0; i < pointCount; i++) {
    arr[i * 3] = color.r;
    arr[i * 3 + 1] = color.g;
    arr[i * 3 + 2] = color.b;
  }
}

function createColorVerts(
  pointCount: number,
  baseColor: THREE.Color,
): Float32Array {
  const arr = new Float32Array(pointCount * 3);
  fillBodyColor(arr, pointCount, baseColor);
  return arr;
}

function updateTipColors(
  arr: Float32Array,
  drawCount: number,
  baseColor: THREE.Color,
  tipColor: THREE.Color,
  tipLen: number,
) {
  const tipStart = Math.max(0, drawCount - tipLen);

  for (let i = tipStart; i < drawCount; i++) {
    const t = (i - tipStart) / Math.max(1, tipLen - 1);
    arr[i * 3] = baseColor.r + (tipColor.r - baseColor.r) * t;
    arr[i * 3 + 1] = baseColor.g + (tipColor.g - baseColor.g) * t;
    arr[i * 3 + 2] = baseColor.b + (tipColor.b - baseColor.b) * t;
  }

  if (tipStart > 0) {
    const pi = (tipStart - 1) * 3;
    arr[pi] = baseColor.r;
    arr[pi + 1] = baseColor.g;
    arr[pi + 2] = baseColor.b;
  }
}

function drawFullLine(a: AnimatedLine, cfg: LineConfig): void {
  const segDone = Math.max(0, a.pointCount - 1);
  a.lineGeo.instanceCount = segDone;
  a.tip.visible = false;
  const lineBase = pathLineDisplayColor(a.pathLineColor, cfg);
  const tipColor = pathTipDisplayColor(a.pathLineColor, cfg);
  updateTipColors(
    a.colorsVert,
    a.pointCount,
    lineBase,
    tipColor,
    cfg.tipPointCount,
  );
  syncLineSegmentBuffers(a.lineGeo, a.positions, a.colorsVert, segDone);
}

function tickAnims(
  anims: AnimatedLine[],
  time: number,
  cfg: LineConfig,
  screenLineWidth?: number,
  size?: THREE.Vector2,
) {
  if (screenLineWidth != null && size) {
    applyScreenLineStyle(cfg, size, screenLineWidth);
  } else {
    applyFatLineSharedStyle(cfg);
  }

  for (const a of anims) {
    const lineBase = pathLineDisplayColor(a.pathLineColor, cfg);
    const tipColorVal = pathTipDisplayColor(a.pathLineColor, cfg);
    const speed = a.cursorSpeed;
    const tipMat = a.tip.material as THREE.MeshBasicMaterial;
    tipMat.color.copy(tipColorVal);
    tipMat.opacity = cfg.tipOpacity;
    a.tip.scale.set(cfg.tipLength, cfg.tipWidth, cfg.tipWidth);

    const lp = a.positions;
    const geo = a.lineGeo;

    if (a.lastLeadSlot >= 0) {
      const s = a.lastLeadSlot * 3;
      lp[s] = a.savedLinePos[0];
      lp[s + 1] = a.savedLinePos[1];
      lp[s + 2] = a.savedLinePos[2];
      a.lastLeadSlot = -1;
    }

    const local = time - a.spawnTime;

    if (local < 0) {
      geo.instanceCount = 0;
      a.tip.visible = false;
      continue;
    }

    const dist = local * speed;

    if (dist >= a.pathLength) {
      const segDone = Math.max(0, a.pointCount - 1);
      geo.instanceCount = segDone;
      a.tip.visible = false;
      updateTipColors(
        a.colorsVert,
        a.pointCount,
        lineBase,
        tipColorVal,
        cfg.tipPointCount,
      );
      syncLineSegmentBuffers(geo, lp, a.colorsVert, segDone);
      continue;
    }

    let baseIdx = 0;
    const cd = a.cumDist;
    while (baseIdx < a.pointCount - 1 && cd[baseIdx + 1] <= dist) {
      baseIdx++;
    }

    const nextIdx = Math.min(baseIdx + 1, a.pointCount - 1);
    const segLen = cd[nextIdx] - cd[baseIdx];
    const frac = segLen > 0 ? (dist - cd[baseIdx]) / segLen : 0;

    const ni = nextIdx * 3;
    const bi = baseIdx * 3;

    a.savedLinePos = [lp[ni], lp[ni + 1], lp[ni + 2]];

    lp[ni] = lp[bi] + (a.savedLinePos[0] - lp[bi]) * frac;
    lp[ni + 1] = lp[bi + 1] + (a.savedLinePos[1] - lp[bi + 1]) * frac;
    lp[ni + 2] = lp[bi + 2] + (a.savedLinePos[2] - lp[bi + 2]) * frac;

    a.tip.visible = true;
    a.tip.position.set(lp[ni], lp[ni + 1], lp[ni + 2]);

    _dir.set(
      a.savedLinePos[0] - lp[bi],
      a.savedLinePos[1] - lp[bi + 1],
      a.savedLinePos[2] - lp[bi + 2],
    );
    if (_dir.lengthSq() > 0.0001) {
      _dir.normalize();
      a.tip.quaternion.setFromUnitVectors(_xAxis, _dir);
    }

    a.lastLeadSlot = nextIdx;

    const drawCount = nextIdx + 1;
    const segDraw = Math.max(0, drawCount - 1);
    geo.instanceCount = segDraw;

    updateTipColors(
      a.colorsVert,
      drawCount,
      lineBase,
      tipColorVal,
      cfg.tipPointCount,
    );
    syncLineSegmentBuffers(geo, lp, a.colorsVert, segDraw);
  }
}

function BackgroundGrid() {
  const matRef = useRef<THREE.LineBasicMaterial>(null);
  const gridSpacing = useLineConfig((s) => s.config.gridSpacing);

  const geo = useMemo(() => {
    const verts: number[] = [];
    const half = GRID_EXTENT / 2;
    for (let x = -half; x <= half; x += gridSpacing) {
      verts.push(x, -half, -0.05, x, half, -0.05);
    }
    for (let y = -half; y <= half; y += gridSpacing) {
      verts.push(-half, y, -0.05, half, y, -0.05);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    return g;
  }, [gridSpacing]);

  useFrame(() => {
    if (!matRef.current) return;
    const cfg = useLineConfig.getState().config;
    matRef.current.color.set(cfg.gridColor);
    matRef.current.opacity = cfg.gridOpacity;
  });

  return (
    <lineSegments geometry={geo}>
      <lineBasicMaterial
        ref={matRef}
        color={0x003040}
        transparent
        opacity={0.06}
      />
    </lineSegments>
  );
}

type TronGridProps = {
  // Optional pre-built paths (e.g. extracted from a GLB via tronLinesFromGLB).
  // Falls back to the in-code abstract grid when omitted.
  paths?: GridPath[];
  // The 80-unit gridlines only make sense for the abstract demo. Real scenes
  // (e.g. the meter-scale table) opt out via showBackgroundGrid={false}.
  showBackgroundGrid?: boolean;
  // When false, every path is drawn at full length with no cursor animation.
  animated?: boolean;
  // Lower bound for playback duration (e.g. camera pan length).
  playbackDuration?: number;
  /** Fixed screen-pixel stroke width; stays visible when zooming out. */
  screenLineWidth?: number;
};

export default function TronGrid({
  paths,
  showBackgroundGrid = true,
  animated = true,
  playbackDuration,
  screenLineWidth,
}: TronGridProps = {}) {
  const groupRef = useRef<THREE.Group>(null);
  const animRef = useRef<AnimatedLine[]>([]);
  const size = useThree((s) => s.size);
  const gridSpacing = useLineConfig((s) => s.config.gridSpacing);
  const lineMaterial =
    screenLineWidth != null
      ? getScreenLineMaterial()
      : getSharedFatLineMaterial();

  const gridPaths = useMemo(() => paths ?? buildScene(42), [paths]);

  useEffect(() => {
    if (!animated) return;

    const syncDuration = () => {
      const speed = useLineConfig.getState().config.cursorSpeed;
      let duration = sceneDuration(gridPaths, speed);
      if (playbackDuration != null) {
        duration = Math.max(duration, playbackDuration);
      }
      useClock.getState().setDuration(duration);
    };

    syncDuration();
    const unsubscribe = useLineConfig.subscribe((state, prev) => {
      if (state.config.cursorSpeed === prev.config.cursorSpeed) return;
      syncDuration();
    });

    return () => {
      unsubscribe();
      useClock.getState().setDuration(20);
    };
  }, [gridPaths, animated, playbackDuration]);

  useEffect(() => {
    const group = groupRef.current;
    if (!group) return;

    const anims: AnimatedLine[] = [];
    const cfg = useLineConfig.getState().config;

    for (const path of gridPaths) {
      if (path.hidden) continue;
      const pts = waypointsToPoints(path.waypoints, gridSpacing);
      const cumDist = computeCumDist(pts);
      const pointCount = pts.length;
      const lineBase = pathLineDisplayColor(path.lineColor, cfg);

      const positions = new Float32Array(pointCount * 3);
      for (let i = 0; i < pointCount; i++) {
        positions[i * 3] = pts[i].x;
        positions[i * 3 + 1] = pts[i].y;
        positions[i * 3 + 2] = pts[i].z;
      }

      const colorsVert = createColorVerts(pointCount, lineBase);

      const lineGeo = new LineGeometry();
      lineGeo.setPositions(positions);
      lineGeo.setColors(colorsVert);
      lineGeo.instanceCount = 0;

      const line = new Line2(lineGeo, lineMaterial);
      line.frustumCulled = false;

      const tipMat = new THREE.MeshBasicMaterial({
        color: pathTipDisplayColor(path.lineColor, cfg),
        transparent: true,
        opacity: cfg.tipOpacity,
        toneMapped: false,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const tip = new THREE.Mesh(sharedTipGeo, tipMat);
      tip.scale.set(cfg.tipLength, cfg.tipWidth, cfg.tipWidth);
      tip.visible = false;

      group.add(line);
      group.add(tip);

      anims.push({
        spawnTime: path.spawnTime,
        pathLength: totalPathLength(path.waypoints),
        cursorSpeed: path.cursorSpeed ?? cfg.cursorSpeed,
        waypoints: path.waypoints,
        line,
        lineGeo,
        tip,
        pointCount,
        cumDist,
        positions,
        colorsVert,
        lastLeadSlot: -1,
        savedLinePos: [0, 0, 0],
        pathLineColor: path.lineColor,
      });
    }

    animRef.current = anims;

    if (!animated) {
      for (const a of anims) {
        drawFullLine(a, cfg);
      }
    }

    // Body vertex colors are baked in at mount; refresh them whenever
    // lineColor changes so already-drawn segments pick up the new color
    // instead of fossilizing the initial one.
    const unsubscribe = useLineConfig.subscribe((state, prev) => {
      if (!lineColorDirty(state.config, prev.config)) return;
      for (const a of anims) {
        const newBase = pathLineDisplayColor(a.pathLineColor, state.config);
        fillBodyColor(a.colorsVert, a.pointCount, newBase);
        const segAll = Math.max(0, a.pointCount - 1);
        syncLineSegmentBuffers(a.lineGeo, a.positions, a.colorsVert, segAll);
      }
    });

    return () => {
      unsubscribe();
      for (const a of anims) {
        group.remove(a.line);
        group.remove(a.tip);
        a.lineGeo.dispose();
        (a.tip.material as THREE.Material).dispose();
      }
    };
  }, [gridPaths, animated, gridSpacing, lineMaterial]);

  useEffect(() => {
    if (animated) return;
    return useLineConfig.subscribe((state, prev) => {
      if (!lineColorDirty(state.config, prev.config)) return;
      for (const a of animRef.current) {
        const lineBase = pathLineDisplayColor(a.pathLineColor, state.config);
        fillBodyColor(a.colorsVert, a.pointCount, lineBase);
        const segAll = Math.max(0, a.pointCount - 1);
        syncLineSegmentBuffers(a.lineGeo, a.positions, a.colorsVert, segAll);
      }
    });
  }, [gridPaths, animated]);

  useFrame((_state, delta) => {
    const cfg = useLineConfig.getState().config;
    if (screenLineWidth != null) {
      applyScreenLineStyle(cfg, size, screenLineWidth);
    } else if (!animated) {
      applyFatLineSharedStyle(cfg);
    }
    if (!animated) return;
    useClock.getState().tick(delta);
    tickAnims(
      animRef.current,
      useClock.getState().time,
      cfg,
      screenLineWidth,
      size,
    );
  });

  return (
    <group ref={groupRef}>
      {showBackgroundGrid ? <BackgroundGrid /> : null}
    </group>
  );
}

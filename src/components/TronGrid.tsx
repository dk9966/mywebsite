import { useRef, useMemo, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import {
  buildScene,
  totalPathLength,
  type Vec3,
} from "../lib/gridBuilder";
import { GRID_SPACING, GRID_EXTENT } from "../lib/constants";
import { useLineConfig, type LineConfig } from "../stores/lineConfig";
import { useClock } from "../stores/clock";

const sharedTipGeo = new THREE.SphereGeometry(0.5, 8, 6);
const _xAxis = new THREE.Vector3(1, 0, 0);
const _dir = new THREE.Vector3();

type AnimatedLine = {
  spawnTime: number;
  pathLength: number;
  waypoints: Vec3[];
  line: THREE.Line;
  glow: THREE.Line;
  tip: THREE.Mesh;
  pointCount: number;
  cumDist: Float32Array;
  posAttr: THREE.BufferAttribute;
  glowPosAttr: THREE.BufferAttribute;
  colorAttr: THREE.BufferAttribute;
  glowColorAttr: THREE.BufferAttribute;
  lastLeadSlot: number;
  savedLinePos: [number, number, number];
  savedGlowPos: [number, number, number];
};

function waypointsToPoints(waypoints: Vec3[]): THREE.Vector3[] {
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
    const steps = Math.max(1, Math.round(maxDelta / GRID_SPACING));
    for (let s = 1; s <= steps; s++) {
      out.push(new THREE.Vector3(
        px + (dx * s) / steps,
        py + (dy * s) / steps,
        pz + (dz * s) / steps,
      ));
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

function createColorAttr(pointCount: number, baseColor: THREE.Color): THREE.BufferAttribute {
  const arr = new Float32Array(pointCount * 3);
  for (let i = 0; i < pointCount; i++) {
    arr[i * 3] = baseColor.r;
    arr[i * 3 + 1] = baseColor.g;
    arr[i * 3 + 2] = baseColor.b;
  }
  const attr = new THREE.BufferAttribute(arr, 3);
  attr.setUsage(THREE.DynamicDrawUsage);
  return attr;
}

function updateTipColors(
  attr: THREE.BufferAttribute,
  drawCount: number,
  baseColor: THREE.Color,
  tipColor: THREE.Color,
  tipLen: number,
) {
  const arr = attr.array as Float32Array;
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

  attr.needsUpdate = true;
}

function tickAnims(anims: AnimatedLine[], time: number, cfg: LineConfig) {
  const lineBase = new THREE.Color(cfg.lineColor);
  const glowBase = new THREE.Color(cfg.glowColor);
  const tipColorVal = new THREE.Color(cfg.tipColor);
  const speed = cfg.cursorSpeed;

  for (const a of anims) {
    const lineMat = a.line.material as THREE.LineBasicMaterial;
    lineMat.transparent = cfg.lineOpacity < 1;
    lineMat.opacity = cfg.lineOpacity;
    const glowMat = a.glow.material as THREE.LineBasicMaterial;
    glowMat.opacity = cfg.glowOpacity;
    const tipMat = a.tip.material as THREE.MeshBasicMaterial;
    tipMat.color.set(cfg.tipColor);
    tipMat.opacity = cfg.tipOpacity;
    a.tip.scale.set(cfg.tipLength, cfg.tipWidth, cfg.tipWidth);

    const lp = a.posAttr.array as Float32Array;
    const gp = a.glowPosAttr.array as Float32Array;

    if (a.lastLeadSlot >= 0) {
      const s = a.lastLeadSlot * 3;
      lp[s] = a.savedLinePos[0];
      lp[s + 1] = a.savedLinePos[1];
      lp[s + 2] = a.savedLinePos[2];
      gp[s] = a.savedGlowPos[0];
      gp[s + 1] = a.savedGlowPos[1];
      gp[s + 2] = a.savedGlowPos[2];
      a.lastLeadSlot = -1;
    }

    const local = time - a.spawnTime;

    if (local < 0) {
      a.line.geometry.setDrawRange(0, 0);
      a.glow.geometry.setDrawRange(0, 0);
      a.tip.visible = false;
      continue;
    }

    const dist = local * speed;

    if (dist >= a.pathLength) {
      a.line.geometry.setDrawRange(0, a.pointCount);
      a.glow.geometry.setDrawRange(0, a.pointCount);
      a.tip.visible = false;
      a.posAttr.needsUpdate = true;
      a.glowPosAttr.needsUpdate = true;
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
    a.savedGlowPos = [gp[ni], gp[ni + 1], gp[ni + 2]];

    lp[ni] = lp[bi] + (a.savedLinePos[0] - lp[bi]) * frac;
    lp[ni + 1] = lp[bi + 1] + (a.savedLinePos[1] - lp[bi + 1]) * frac;
    lp[ni + 2] = lp[bi + 2] + (a.savedLinePos[2] - lp[bi + 2]) * frac;

    gp[ni] = gp[bi] + (a.savedGlowPos[0] - gp[bi]) * frac;
    gp[ni + 1] = gp[bi + 1] + (a.savedGlowPos[1] - gp[bi + 1]) * frac;
    gp[ni + 2] = gp[bi + 2] + (a.savedGlowPos[2] - gp[bi + 2]) * frac;

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
    a.posAttr.needsUpdate = true;
    a.glowPosAttr.needsUpdate = true;

    const drawCount = nextIdx + 1;
    a.line.geometry.setDrawRange(0, drawCount);
    a.glow.geometry.setDrawRange(0, drawCount);

    updateTipColors(a.colorAttr, drawCount, lineBase, tipColorVal, cfg.tipPointCount);
    updateTipColors(a.glowColorAttr, drawCount, glowBase, tipColorVal, cfg.tipPointCount);
  }
}

function BackgroundGrid() {
  const matRef = useRef<THREE.LineBasicMaterial>(null);

  const geo = useMemo(() => {
    const verts: number[] = [];
    const half = GRID_EXTENT / 2;
    for (let x = -half; x <= half; x += GRID_SPACING) {
      verts.push(x, -half, -0.05, x, half, -0.05);
    }
    for (let y = -half; y <= half; y += GRID_SPACING) {
      verts.push(-half, y, -0.05, half, y, -0.05);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    return g;
  }, []);

  useFrame(() => {
    if (!matRef.current) return;
    const cfg = useLineConfig.getState().config;
    matRef.current.color.set(cfg.gridColor);
    matRef.current.opacity = cfg.gridOpacity;
  });

  return (
    <lineSegments geometry={geo}>
      <lineBasicMaterial ref={matRef} color={0x003040} transparent opacity={0.06} />
    </lineSegments>
  );
}

export default function TronGrid() {
  const groupRef = useRef<THREE.Group>(null);
  const animRef = useRef<AnimatedLine[]>([]);

  const gridPaths = useMemo(() => buildScene(42), []);

  useEffect(() => {
    const group = groupRef.current;
    if (!group) return;

    const anims: AnimatedLine[] = [];
    const cfg = useLineConfig.getState().config;
    const lineBase = new THREE.Color(cfg.lineColor);
    const glowBase = new THREE.Color(cfg.glowColor);

    for (const path of gridPaths) {
      const pts = waypointsToPoints(path.waypoints);
      const cumDist = computeCumDist(pts);

      const colorAttr = createColorAttr(pts.length, lineBase);
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const posAttr = geo.getAttribute("position") as THREE.BufferAttribute;
      posAttr.setUsage(THREE.DynamicDrawUsage);
      geo.setAttribute("color", colorAttr);
      geo.setDrawRange(0, 0);

      const line = new THREE.Line(
        geo,
        new THREE.LineBasicMaterial({ vertexColors: true }),
      );

      const glowColorAttr = createColorAttr(pts.length, glowBase);
      const glowGeo = new THREE.BufferGeometry().setFromPoints(pts);
      const glowPosAttr = glowGeo.getAttribute("position") as THREE.BufferAttribute;
      glowPosAttr.setUsage(THREE.DynamicDrawUsage);
      glowGeo.setAttribute("color", glowColorAttr);
      glowGeo.setDrawRange(0, 0);
      const glow = new THREE.Line(
        glowGeo,
        new THREE.LineBasicMaterial({
          vertexColors: true,
          transparent: true,
          opacity: cfg.glowOpacity,
        }),
      );

      const tipMat = new THREE.MeshBasicMaterial({
        color: cfg.tipColor,
        transparent: true,
        opacity: cfg.tipOpacity,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const tip = new THREE.Mesh(sharedTipGeo, tipMat);
      tip.scale.set(cfg.tipLength, cfg.tipWidth, cfg.tipWidth);
      tip.visible = false;

      group.add(glow);
      group.add(line);
      group.add(tip);

      anims.push({
        spawnTime: path.spawnTime,
        pathLength: totalPathLength(path.waypoints),
        waypoints: path.waypoints,
        line,
        glow,
        tip,
        pointCount: pts.length,
        cumDist,
        posAttr,
        glowPosAttr,
        colorAttr,
        glowColorAttr,
        lastLeadSlot: -1,
        savedLinePos: [0, 0, 0],
        savedGlowPos: [0, 0, 0],
      });
    }

    animRef.current = anims;

    return () => {
      for (const a of anims) {
        group.remove(a.line);
        group.remove(a.glow);
        group.remove(a.tip);
        a.line.geometry.dispose();
        (a.line.material as THREE.Material).dispose();
        a.glow.geometry.dispose();
        (a.glow.material as THREE.Material).dispose();
        (a.tip.material as THREE.Material).dispose();
      }
    };
  }, [gridPaths]);

  useFrame((_, delta) => {
    useClock.getState().tick(delta);
    tickAnims(animRef.current, useClock.getState().time, useLineConfig.getState().config);
  });

  return (
    <group ref={groupRef}>
      <BackgroundGrid />
    </group>
  );
}

import { Html, OrbitControls } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { Font } from "three/addons/loaders/FontLoader.js";
import { TextGeometry } from "three/addons/geometries/TextGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import { DISPLAY_FONTS, loadFont, printable, withLetterSpacing } from "./fonts";
import { makeMaterials } from "./materials";
import { WORD_IDS, applyCase, useTextLab, type SceneSettings, type WordId, type WordStyle } from "./store";

type Size = { w: number; h: number };

const DEFAULT_DISTANCE = 19;
const GALLERY_DISTANCE = 31;

// Keeps showing the previous font while the next one streams in, so switching
// fonts swaps in place instead of blinking out.
function useLoadedFont(id: string): Font | null {
  const [loaded, setLoaded] = useState<Font | null>(null);
  useEffect(() => {
    let live = true;
    loadFont(id)
      .then((font) => live && setLoaded(font))
      .catch((err) => console.warn(`[text] font ${id} failed`, err));
    return () => {
      live = false;
    };
  }, [id]);
  return loaded;
}

// One extruded word: geometry centred on the origin, caps/sides materials,
// optional edge lines. Reports its size so layouts can space words.
function WordMesh({
  style,
  fontId,
  onMeasure,
}: {
  style: WordStyle;
  fontId: string;
  onMeasure?: (size: Size) => void;
}) {
  const font = useLoadedFont(fontId);
  const { text, textCase, size, letterSpacing, weight, depth, curveSegments, bevel, bevelThickness, bevelSize, bevelSegments } =
    style;

  const geometry = useMemo(() => {
    if (!font) return null;
    const spaced = withLetterSpacing(font, letterSpacing);
    const g = new TextGeometry(printable(spaced, applyCase(text, textCase)), {
      font: spaced,
      size,
      depth,
      curveSegments,
      // Weight rides on the bevel offset: with no bevel size the caps and
      // walls share one contour, so the whole glyph grows or shrinks evenly.
      bevelEnabled: bevel || weight !== 0,
      bevelThickness: bevel ? bevelThickness : 0,
      bevelSize: bevel ? bevelSize : 0,
      bevelSegments: bevel ? bevelSegments : 1,
      bevelOffset: weight * size,
    });
    g.computeBoundingBox();
    const c = g.boundingBox!.getCenter(new THREE.Vector3());
    g.translate(-c.x, -c.y, -c.z);
    g.computeBoundingBox();
    return g;
  }, [font, text, textCase, size, letterSpacing, weight, depth, curveSegments, bevel, bevelThickness, bevelSize, bevelSegments]);
  useEffect(() => () => geometry?.dispose(), [geometry]);

  useEffect(() => {
    if (!geometry || !onMeasure) return;
    const s = geometry.boundingBox!.getSize(new THREE.Vector3());
    onMeasure({ w: s.x, h: s.y });
  }, [geometry, onMeasure]);

  const materials = useMemo(
    () => (geometry ? makeMaterials(style, geometry.boundingBox!) : null),
    // Rebuild only on fields the materials read.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      geometry,
      style.fill,
      style.faceColor,
      style.sideColor,
      style.accentColor,
      style.glow,
      style.fxScale,
      style.fxSpeed,
      style.size,
      style.bodyOpacity,
      style.bodyFill,
      style.bodyColor,
    ],
  );
  useEffect(
    () => () => {
      materials?.forEach((m) => m.dispose());
    },
    [materials],
  );

  // Outline lines: the Tron fill, or the "Edge lines" toggle on any fill.
  // three's fat lines (LineSegments2) give real pixel widths, which plain
  // GL lines can't; resolution must track the canvas size.
  const viewSize = useThree((s) => s.size);
  const isTron = style.fill === "tron";
  const showLines = isTron || style.edges;
  const lineGeometry = useMemo(() => {
    if (!geometry || !showLines) return null;
    const edges = new THREE.EdgesGeometry(geometry, 28);
    const g = new LineSegmentsGeometry().fromEdgesGeometry(edges);
    edges.dispose();
    return g;
  }, [geometry, showLines]);
  useEffect(() => () => lineGeometry?.dispose(), [lineGeometry]);

  const lineColor = isTron ? style.faceColor : style.edgeColor;
  const lineGain = isTron ? style.glow : 1.5;
  const lines = useMemo(() => {
    if (!lineGeometry) return null;
    const mat = new LineMaterial({
      color: new THREE.Color(lineColor).multiplyScalar(lineGain),
      linewidth: style.lineWidth,
      toneMapped: false,
    });
    mat.resolution.set(viewSize.width, viewSize.height);
    const obj = new LineSegments2(lineGeometry, mat);
    obj.raycast = () => {}; // clicks (gallery picking) should hit the body, not the lines
    return obj;
  }, [lineGeometry, lineColor, lineGain, style.lineWidth, viewSize.width, viewSize.height]);
  useEffect(() => () => (lines?.material as THREE.Material | undefined)?.dispose(), [lines]);

  useFrame(({ clock }) => {
    const m = materials?.[0];
    if (m instanceof THREE.ShaderMaterial) m.uniforms.time.value = clock.elapsedTime;
  });

  if (!geometry || !materials) return null;
  return (
    <>
      <mesh geometry={geometry} material={materials} />
      {lines && <primitive object={lines} />}
    </>
  );
}

type Placement = { x: number; y: number; z: number; ry: number };

function Word({
  id,
  index,
  placement,
  onMeasure,
}: {
  id: WordId;
  index: number;
  placement: Placement;
  onMeasure: (id: WordId, size: Size) => void;
}) {
  const style = useTextLab((s) => s.words[id]);
  const font = useTextLab((s) => s.font);
  const motion = useTextLab((s) => s.scene.motion);
  const motionSpeed = useTextLab((s) => s.scene.motionSpeed);
  const motionRef = useRef<THREE.Group>(null);
  const angle = useRef(0);

  const measure = useCallback((size: Size) => onMeasure(id, size), [id, onMeasure]);

  // Idle motion is opt-in (default Still); manual orbiting is the main way to turn the text.
  useFrame(({ clock }, dt) => {
    const m = motionRef.current;
    if (!m) return;
    const t = clock.elapsedTime * motionSpeed + index * 1.3;
    if (motion === "spin") angle.current += dt * motionSpeed * 1.2;
    m.position.y = motion === "float" ? Math.sin(t * 1.4) * 0.18 : 0;
    m.rotation.y = motion === "sway" ? Math.sin(t) * 0.35 : motion === "spin" ? angle.current : 0;
    m.rotation.x = motion === "float" ? Math.sin(t * 0.9) * 0.08 : 0;
    m.rotation.z = motion === "float" ? Math.sin(t * 0.7) * 0.04 : 0;
  });

  return (
    <group position={[placement.x, placement.y, placement.z]} rotation-y={placement.ry}>
      <group ref={motionRef}>
        <WordMesh style={style} fontId={font} onMeasure={measure} />
      </group>
    </group>
  );
}

function computeLayout(scene: SceneSettings, sizes: Size[]): Placement[] {
  const { layout, align, gap } = scene;
  const n = sizes.length;
  const maxW = Math.max(...sizes.map((s) => s.w));
  const maxH = Math.max(...sizes.map((s) => s.h));
  const alignX = (w: number, cellW: number) =>
    align === "left" ? -cellW / 2 + w / 2 : align === "right" ? cellW / 2 - w / 2 : 0;

  if (layout === "row") {
    const total = sizes.reduce((a, s) => a + s.w, 0) + gap * 2 * (n - 1);
    let x = -total / 2;
    return sizes.map((s) => {
      const p = { x: x + s.w / 2, y: 0, z: 0, ry: 0 };
      x += s.w + gap * 2;
      return p;
    });
  }
  if (layout === "grid") {
    const cw = maxW + gap * 2;
    const ch = maxH + gap * 2;
    return sizes.map((s, i) => ({
      x: (i % 2 === 0 ? -cw / 2 : cw / 2) + alignX(s.w, maxW),
      y: i < 2 ? ch / 2 : -ch / 2,
      z: 0,
      ry: 0,
    }));
  }
  if (layout === "ring") {
    const r = Math.max(maxW * 0.75, 2.5) + gap;
    return sizes.map((_, i) => {
      const a = (i / n) * Math.PI * 2;
      return { x: Math.sin(a) * r, y: 0, z: Math.cos(a) * r, ry: a };
    });
  }
  // stack + cascade share the vertical rhythm.
  const total = sizes.reduce((a, s) => a + s.h, 0) + gap * (n - 1);
  let y = total / 2;
  return sizes.map((s, i) => {
    const p = { x: alignX(s.w, maxW), y: y - s.h / 2, z: 0, ry: 0 };
    if (layout === "cascade") {
      p.x += (i - (n - 1) / 2) * maxW * 0.18;
      p.z = ((n - 1) / 2 - i) * 1.4;
    }
    y -= s.h + gap;
    return p;
  });
}

function Words() {
  const scene = useTextLab((s) => s.scene);
  const [sizes, setSizes] = useState<Record<WordId, Size>>(() =>
    Object.fromEntries(WORD_IDS.map((id) => [id, { w: 5, h: 1 }])) as Record<WordId, Size>,
  );
  const onMeasure = useCallback(
    (id: WordId, size: Size) =>
      setSizes((prev) =>
        Math.abs(prev[id].w - size.w) < 1e-4 && Math.abs(prev[id].h - size.h) < 1e-4
          ? prev
          : { ...prev, [id]: size },
      ),
    [],
  );
  const placements = computeLayout(
    scene,
    WORD_IDS.map((id) => sizes[id]),
  );

  return (
    <>
      {WORD_IDS.map((id, i) => (
        <Word key={id} id={id} index={i} placement={placements[i]} onMeasure={onMeasure} />
      ))}
    </>
  );
}

// Font gallery ----------------------------------------------------------------

const TILE_W = 3.6;
const TILE_H = 1.7;
const GALLERY_COLS = 7;

function GalleryTile({
  fontId,
  label,
  style,
  active,
  x,
  y,
  onPick,
}: {
  fontId: string;
  label: string;
  style: WordStyle;
  active: boolean;
  x: number;
  y: number;
  onPick: (id: string) => void;
}) {
  const [size, setSize] = useState<Size | null>(null);
  const scale = size ? Math.min((TILE_W - 0.5) / size.w, (TILE_H - 0.6) / size.h) : 0.001;
  return (
    <group position={[x, y, 0]}>
      <group
        scale={scale}
        position-y={0.18}
        onClick={(e) => {
          // A drag that started on a tile is an orbit/pan, not a pick.
          if (e.delta > 4) return;
          e.stopPropagation();
          onPick(fontId);
        }}
        onPointerOver={() => (document.body.style.cursor = "pointer")}
        onPointerOut={() => (document.body.style.cursor = "")}
      >
        <WordMesh style={style} fontId={fontId} onMeasure={setSize} />
      </group>
      <Html center position={[0, -TILE_H / 2 + 0.12, 0]} style={{ pointerEvents: "none" }}>
        <div className={`text-lab-gallery-label${active ? " is-active" : ""}`}>{label}</div>
      </Html>
    </group>
  );
}

function Gallery() {
  const font = useTextLab((s) => s.font);
  const style = useTextLab((s) => s.words[s.target === "all" ? "project" : s.target]);
  const setFont = useTextLab((s) => s.setFont);
  const rows = Math.ceil(DISPLAY_FONTS.length / GALLERY_COLS);
  // Gallery tiles ignore spacing/size so every face is compared at one scale.
  const tileStyle = useMemo(() => ({ ...style, size: 1 }), [style]);
  return (
    <>
      {DISPLAY_FONTS.map((f, i) => {
        const col = i % GALLERY_COLS;
        const row = Math.floor(i / GALLERY_COLS);
        return (
          <GalleryTile
            key={f.id}
            fontId={f.id}
            label={f.label}
            style={tileStyle}
            active={f.id === font}
            x={(col - (GALLERY_COLS - 1) / 2) * TILE_W}
            y={((rows - 1) / 2 - row) * TILE_H}
            onPick={setFont}
          />
        );
      })}
    </>
  );
}

// View ------------------------------------------------------------------------

type OrbitLike = { target: THREE.Vector3; update: () => void };

// Snap the camera back to the default framing on first mount, when the layout
// changes (the gallery needs a wider shot), and on the panel's Reset view.
function ResetView() {
  const layout = useTextLab((s) => s.scene.layout);
  const nonce = useTextLab((s) => s.viewNonce);
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as unknown as OrbitLike | null;
  useEffect(() => {
    if (!controls) return;
    controls.target.set(0, 0, 0);
    camera.position.set(0, 0.6, layout === "gallery" ? GALLERY_DISTANCE : DEFAULT_DISTANCE);
    controls.update();
  }, [camera, controls, layout, nonce]);
  return null;
}

// Shift the projection centre left by half the panel's width so the words
// centre in the visible area instead of sliding under the panel.
const PANEL_PX = 344;

function PanelViewOffset() {
  const panelOpen = useTextLab((s) => s.panelOpen);
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const { width, height } = useThree((s) => s.size);
  useEffect(() => {
    // The panel docks to the bottom on narrow screens (see text-lab.css).
    if (panelOpen && width > 760) camera.setViewOffset(width, height, PANEL_PX / 2, 0, width, height);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
  }, [camera, panelOpen, width, height]);
  return null;
}

// Dev handle for poking at the scene from the console / CDP scripts.
function DevHandle() {
  const state = useThree();
  useEffect(() => {
    if (import.meta.env.DEV) (window as unknown as { __textLab: unknown }).__textLab = state;
  }, [state]);
  return null;
}

function Stage() {
  const scene = useTextLab((s) => s.scene);
  return (
    <>
      <color attach="background" args={["#000000"]} />
      {/* Left-drag orbits, right-drag / shift-drag pans, wheel and pinch zoom. */}
      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.08}
        minDistance={1.5}
        maxDistance={200}
        zoomSpeed={1.1}
        autoRotate={scene.autoRotate}
        autoRotateSpeed={scene.autoRotateSpeed}
      />
      <ResetView />
      <PanelViewOffset />
      <DevHandle />
      {scene.layout === "gallery" ? <Gallery /> : <Words />}
      <EffectComposer>
        <Bloom
          mipmapBlur
          intensity={scene.bloom}
          luminanceThreshold={scene.bloomThreshold}
          luminanceSmoothing={0.2}
          radius={0.7}
        />
      </EffectComposer>
    </>
  );
}

export default function TextScene({ active }: { active: boolean }) {
  return (
    <Canvas
      // Pause rendering while the hero is scrolled out of view.
      frameloop={active ? "always" : "never"}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: false }}
      camera={{ position: [0, 0.6, DEFAULT_DISTANCE], fov: 40, near: 0.1, far: 500 }}
    >
      <Stage />
    </Canvas>
  );
}

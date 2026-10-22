import { useEffect, useMemo } from "react";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { Vec3 } from "./caveAssets";
import { CAVE_FLAGS } from "./caveFlags";
import { TITLE_POWER } from "./caveStartup";
import layoutFile from "./labelLayout.json";

/** The type board's capital height is about 110 px; one board pixel is 0.0052 m, so every title shares this type size. */
const BOARD_CAP = 110;
const CAP_METRES = BOARD_CAP * 0.0052;
/** Distance-field texels per cap height, and the distance (in caps) each side of an edge it spans; see make_label_sdf.py (2 texels and 14 px per board pixel). */
const TEXELS_PER_CAP = 2 * BOARD_CAP;
const SPREAD = 14 / BOARD_CAP;
/** Widens every edge by this many caps (0 = the lettering as drawn). */
const BIAS = 0;
/** How quickly the neon halo fades outside the letter, per cap height. */
const HALO_FALLOFF = 40;
const SAVE_ROUTE = "/__save-cave-labels";

type Placement = { position: Vec3; scale: number };
type Layout = Record<string, Placement>;

const TITLES = [
  { title: "Projects", file: "projects.png" },
  { title: "About Me", file: "about.png" },
  { title: "Experiences", file: "experiences.png" },
  { title: "Contact", file: "contact.png" },
];

const url = (file: string) => new URL(`../../models/cave/labels/${file}`, import.meta.url).href;

/**
 * Billboard quad: always faces the camera, `uSize` is its size in metres.
 * The fragment shader reads the distance field, so the edge is a clean
 * one-pixel ramp at any size, with a faint neon halo drawn from the same field.
 */
const VERTEX = /* glsl */ `
  uniform vec2 uSize;
  varying vec2 vUv;
  void main() {
    vUv = uv;
    vec4 centre = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
    centre.xy += position.xy * uSize;
    gl_Position = projectionMatrix * centre;
  }
`;

const FRAGMENT = /* glsl */ `
  uniform sampler2D uField;
  uniform vec3 uCore;
  uniform vec3 uHalo;
  uniform float uSpread;
  uniform float uBias;
  uniform float uFalloff;
  uniform float uOutline;
  uniform float uLevel;
  varying vec2 vUv;
  void main() {
    // Signed distance in cap heights, positive inside the glyph, widened by the stroke bias.
    float d = (texture2D(uField, vUv).r - 0.5) * 2.0 * uSpread + uBias;
    float edge = max(fwidth(d), 1e-4);
    float core = clamp(d / edge + 0.5, 0.0, 1.0);
    // Zero by the edge of the stored field, so the quad's border never shows.
    float reach = uSpread - uBias;
    float fade = exp(-reach * uFalloff);
    float halo = max(exp(-max(-d, 0.0) * uFalloff) - fade, 0.0) / (1.0 - fade) * (1.0 - core);
    vec3 colour = (uCore * core + uHalo * halo) * uLevel;
    if (uOutline > 0.5) {
      vec2 w = fwidth(vUv) * 1.5;
      vec2 inner = step(w, vUv) * step(w, 1.0 - vUv);
      colour += vec3(1.0, 0.55, 0.1) * (1.0 - inner.x * inner.y);
    }
    gl_FragColor = vec4(colour, 1.0);
  }
`;

type Title = {
  name: string;
  mesh: THREE.Mesh;
  material: THREE.ShaderMaterial;
  /** Quad size in metres at scale 1. */
  baseSize: THREE.Vector2;
};

function placementOf(name: string, layout: Layout): Placement {
  return layout[name] ?? { position: [0, 0, 0], scale: 1 };
}

function applyPlacement(title: Title, placement: Placement) {
  title.mesh.position.set(...placement.position);
  title.material.uniforms.uSize.value.copy(title.baseSize).multiplyScalar(placement.scale);
}

/** The section titles floating above each island, in neon, crisp at any size. */
export function CaveLabels() {
  const invalidate = useThree((s) => s.invalidate);
  const layout = useMemo(() => ({ current: structuredClone(layoutFile) as unknown as Layout }), []);
  const titles = useMemo<Title[]>(() => {
    const quad = new THREE.PlaneGeometry(1, 1);
    return TITLES.map(({ title, file }, i) => {
      const material = new THREE.ShaderMaterial({
        vertexShader: VERTEX,
        fragmentShader: FRAGMENT,
        uniforms: {
          uField: { value: null },
          uSize: { value: new THREE.Vector2(1, 1) },
          // Scene-linear; kept at or under 1 so the pixel filter never smears the edge.
          uCore: { value: new THREE.Color(0.02, 1.7, 2.1) },
          uHalo: { value: new THREE.Color(0, 0.3, 0.6) },
          uSpread: { value: SPREAD },
          uBias: { value: BIAS },
          uFalloff: { value: HALO_FALLOFF },
          uOutline: { value: 0 },
          // Flickers on after the cave's lights (caveStartup.ts).
          uLevel: TITLE_POWER[i],
        },
        blending: THREE.AdditiveBlending,
        transparent: true,
        depthWrite: false,
        toneMapped: false,
      });
      const mesh = new THREE.Mesh(quad, material);
      mesh.name = `title-${title}`;
      mesh.renderOrder = 10;
      // The vertex shader moves the quad; its bounds say nothing about where it draws.
      mesh.frustumCulled = false;
      mesh.visible = false;
      const entry: Title = { name: title, mesh, material, baseSize: new THREE.Vector2(1, 1) };
      new THREE.TextureLoader().load(url(file), (texture) => {
        texture.colorSpace = THREE.NoColorSpace;
        texture.anisotropy = 8;
        texture.needsUpdate = true;
        const image = texture.image as HTMLImageElement;
        entry.baseSize.set(image.width, image.height).multiplyScalar(CAP_METRES / TEXELS_PER_CAP);
        material.uniforms.uField.value = texture;
        applyPlacement(entry, placementOf(title, layout.current));
        mesh.visible = true;
        invalidate();
      });
      return entry;
    });
  }, [invalidate, layout]);

  useEffect(() => {
    const apply = () => {
      for (const title of titles) applyPlacement(title, placementOf(title.name, layout.current));
      invalidate();
    };
    apply();
    // The dev server does not watch the layout file (a save must not reload the
    // page), so its imported copy goes stale: read the file as it is on disk.
    if (!import.meta.env.DEV) return;
    let live = true;
    fetch(SAVE_ROUTE)
      .then((response) => (response.ok ? response.json() : null))
      .then((saved: Layout | null) => {
        if (!live || !saved) return;
        // In place: the editor holds this same object.
        Object.assign(layout.current, saved);
        apply();
      })
      .catch(() => {});
    return () => { live = false; };
  }, [titles, layout, invalidate]);

  useEffect(
    () => () => {
      titles[0]?.mesh.geometry.dispose();
      for (const title of titles) {
        (title.material.uniforms.uField.value as THREE.Texture | null)?.dispose();
        title.material.dispose();
      }
    },
    [titles],
  );

  useLabelEditor(titles, layout.current);

  return (
    <>
      {titles.map((title) => (
        <primitive key={title.name} object={title.mesh} />
      ))}
    </>
  );
}

/**
 * Dev editor: drag a title to move it (it stays at the same distance from the
 * camera), scroll over it to resize it. Every change is written to
 * `labelLayout.json`, which is what the cave ships with.
 */
function useLabelEditor(titles: Title[], layout: Layout) {
  const gl = useThree((s) => s.gl);
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const invalidate = useThree((s) => s.invalidate);

  useEffect(() => {
    if (!CAVE_FLAGS.editLabels) return;
    const canvas = gl.domElement;
    const host = canvas.parentElement ?? document.body;
    const hud = document.createElement("div");
    hud.style.cssText =
      "position:absolute;left:12px;bottom:12px;padding:8px 12px;border-radius:6px;font:12px/1.4 ui-monospace,Menlo,monospace;" +
      "color:#9fe;background:rgba(5,15,20,.8);border:1px solid rgba(80,220,255,.35);pointer-events:none;z-index:5;white-space:pre";
    host.appendChild(hud);
    const say = (text: string) => { hud.textContent = text; };
    const hint = "Titles: drag to move · scroll over one to resize";
    say(hint);

    let selected: Title | null = null;
    let drag: { title: Title; offset: THREE.Vector3 } | null = null;
    let saveTimer: number | undefined;

    const select = (next: Title | null) => {
      if (selected === next) return;
      if (selected) selected.material.uniforms.uOutline.value = 0;
      selected = next;
      if (selected) selected.material.uniforms.uOutline.value = 1;
      invalidate();
    };

    const ndcOf = (event: { clientX: number; clientY: number }) => {
      const rect = canvas.getBoundingClientRect();
      return new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -(((event.clientY - rect.top) / rect.height) * 2 - 1),
      );
    };

    /** The title under the pointer, judged by the rectangle it covers on screen. */
    const titleAt = (event: { clientX: number; clientY: number }) => {
      camera.updateMatrixWorld();
      const pointer = ndcOf(event);
      const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      const up = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
      let hit: Title | null = null;
      let nearest = Infinity;
      for (const title of titles) {
        if (!title.mesh.visible) continue;
        const size = title.material.uniforms.uSize.value as THREE.Vector2;
        const centre = title.mesh.position;
        const corner = (sx: number, sy: number) =>
          centre.clone().addScaledVector(right, (sx * size.x) / 2).addScaledVector(up, (sy * size.y) / 2).project(camera);
        const a = corner(-1, -1);
        const b = corner(1, 1);
        if (pointer.x < a.x || pointer.x > b.x || pointer.y < a.y || pointer.y > b.y) continue;
        const depth = centre.distanceTo(camera.position);
        if (depth < nearest) { nearest = depth; hit = title; }
      }
      return hit;
    };

    const planePoint = (event: { clientX: number; clientY: number }, through: THREE.Vector3) => {
      const ray = new THREE.Raycaster();
      ray.setFromCamera(ndcOf(event), camera);
      const normal = camera.getWorldDirection(new THREE.Vector3());
      const point = new THREE.Vector3();
      return ray.ray.intersectPlane(new THREE.Plane().setFromNormalAndCoplanarPoint(normal, through), point) ? point : null;
    };

    const save = () => {
      window.clearTimeout(saveTimer);
      say("Saving…");
      saveTimer = window.setTimeout(async () => {
        try {
          const body = JSON.stringify(layout, (_, v) => (typeof v === "number" ? Math.round(v * 1000) / 1000 : v), 2);
          const response = await fetch(SAVE_ROUTE, { method: "POST", headers: { "Content-Type": "application/json" }, body });
          say(response.ok ? `${hint}\nSaved to labelLayout.json` : "Save failed");
        } catch {
          say("Save failed");
        }
      }, 300);
    };

    const onDown = (event: PointerEvent) => {
      if (event.button !== 0) return;
      const title = titleAt(event);
      select(title);
      if (!title) return;
      const point = planePoint(event, title.mesh.position);
      if (!point) return;
      drag = { title, offset: title.mesh.position.clone().sub(point) };
      canvas.setPointerCapture(event.pointerId);
      event.preventDefault();
    };

    const onMove = (event: PointerEvent) => {
      if (!drag) {
        canvas.style.cursor = titleAt(event) ? "grab" : "";
        return;
      }
      canvas.style.cursor = "grabbing";
      const point = planePoint(event, drag.title.mesh.position);
      if (!point) return;
      drag.title.mesh.position.copy(point.add(drag.offset));
      const placement = placementOf(drag.title.name, layout);
      placement.position = drag.title.mesh.position.toArray() as Vec3;
      layout[drag.title.name] = placement;
      invalidate();
    };

    const onUp = (event: PointerEvent) => {
      if (!drag) return;
      canvas.releasePointerCapture(event.pointerId);
      drag = null;
      canvas.style.cursor = "grab";
      save();
    };

    const onWheel = (event: WheelEvent) => {
      const title = titleAt(event) ?? selected;
      if (!title) return;
      event.preventDefault();
      const placement = placementOf(title.name, layout);
      placement.scale = THREE.MathUtils.clamp(placement.scale * Math.exp(-event.deltaY * 0.0015), 0.2, 6);
      placement.position = title.mesh.position.toArray() as Vec3;
      layout[title.name] = placement;
      applyPlacement(title, placement);
      select(title);
      invalidate();
      save();
    };

    canvas.addEventListener("pointerdown", onDown);
    canvas.addEventListener("pointermove", onMove);
    canvas.addEventListener("pointerup", onUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      canvas.removeEventListener("pointerdown", onDown);
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerup", onUp);
      canvas.removeEventListener("wheel", onWheel);
      window.clearTimeout(saveTimer);
      select(null);
      canvas.style.cursor = "";
      hud.remove();
    };
  }, [gl, camera, invalidate, titles, layout]);
}

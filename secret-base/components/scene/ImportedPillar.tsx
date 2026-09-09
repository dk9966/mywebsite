import { Suspense, useMemo } from "react";
import * as THREE from "three";
import { useGLTF } from "@react-three/drei";
import { RectAreaLightUniformsLib } from "three/addons/lights/RectAreaLightUniformsLib.js";
import { rebindMaterials } from "./materials";
import { HoloPanel } from "./HoloPanel";
import { Screen } from "./Screen";
import { StationLights } from "./stationLights";

// RectAreaLight needs this once per page; the station lamps use it.
RectAreaLightUniformsLib.init();

export const PILLAR_GLB_URL = new URL(
  "../../models/pillar.glb",
  import.meta.url,
).href;

const ZERO: [number, number, number] = [0, 0, 0];

function worldPos(obj: THREE.Object3D): THREE.Vector3 {
  const p = new THREE.Vector3();
  obj.updateWorldMatrix(true, false);
  obj.getWorldPosition(p);
  return p;
}

function floorTop(scene: THREE.Object3D): number {
  const floor = scene.getObjectByName("deck_floor_b");
  if (!floor) return 0;
  const box = new THREE.Box3().setFromObject(floor);
  return box.max.y;
}

/** Plane faces +Z; lookAt aims -Z, so spin 180° after aiming at the seat. */
function facingSeat(from: THREE.Vector3, seat: THREE.Vector3): THREE.Euler {
  const dummy = new THREE.Object3D();
  dummy.position.copy(from);
  dummy.lookAt(seat);
  dummy.rotateY(Math.PI);
  dummy.rotateX(-0.08);
  return dummy.rotation.clone();
}

function Model() {
  const { scene } = useGLTF(PILLAR_GLB_URL);

  const layout = useMemo(() => {
    rebindMaterials(scene);
    scene.updateWorldMatrix(true, true);

    const pillar = scene.getObjectByName("island_pillar_workshop");
    const main = scene.getObjectByName("holoLocator_main");
    const left = scene.getObjectByName("holoLocator_left");
    const right = scene.getObjectByName("holoLocator_right");
    const seatObj = scene.getObjectByName("holoLocator_seat");

    const origin = pillar ? worldPos(pillar) : new THREE.Vector3();
    const seat = seatObj ? worldPos(seatObj) : origin.clone().add(new THREE.Vector3(0, 1.15, 1));

    const pose = (obj: THREE.Object3D | undefined) => {
      if (!obj) return null;
      const p = worldPos(obj);
      return { position: p, rotation: facingSeat(p, seat) };
    };

    return {
      recenter: [-origin.x, -floorTop(scene), -origin.z] as [
        number,
        number,
        number,
      ],
      main: pose(main),
      left: pose(left),
      right: pose(right),
    };
  }, [scene]);

  return (
    <group name="importedPillar" position={layout.recenter}>
      {/* Blender world shader: almost black, strength 0.12 */}
      <ambientLight intensity={0.12} color="#080f1f" />
      <StationLights />
      <primitive object={scene} />
      {layout.main && (
        <group
          position={layout.main.position.toArray()}
          rotation={layout.main.rotation}
        >
          <HoloPanel position={ZERO} width={1.55} glow={2.8} />
        </group>
      )}
      {layout.left && (
        <group
          position={layout.left.position.toArray()}
          rotation={layout.left.rotation}
        >
          <Screen
            variant="radar"
            round
            frame={false}
            width={0.5}
            position={ZERO}
            glow={3.2}
            transparent
          />
        </group>
      )}
      {layout.right && (
        <group
          position={layout.right.position.toArray()}
          rotation={layout.right.rotation}
        >
          <Screen
            variant="ui"
            frame={false}
            width={0.66}
            height={0.42}
            position={ZERO}
            glow={3.0}
            transparent
          />
        </group>
      )}
    </group>
  );
}

/** Workshop pillar from base.blend, with live holographic screens on the locators. */
export function ImportedPillar() {
  return (
    <Suspense fallback={null}>
      <Model />
    </Suspense>
  );
}

useGLTF.preload(PILLAR_GLB_URL);

import { useMemo } from "react";
import { Billboard } from "@react-three/drei";
import * as THREE from "three";
import { StationHeading } from "./StationHeading";

const HEADING_LIFT = 3.7;

/** Web-only labels, centered at the same height above each live deck. */
export function StationIslandHeadings({ scene, lightColor }: {
  scene: THREE.Object3D;
  lightColor: THREE.Color;
}) {
  const headings = useMemo(() => {
    scene.updateWorldMatrix(true, true);
    // Convert back to model coordinates if this live model is already recentered.
    const inverse = scene.matrixWorld.clone().invert();
    return [
      { floor: "deck_floor_b", title: "Projects" },
      { floor: "deck_floor_experience", title: "Experiences" },
      { floor: "deck_floor_about", title: "About Me" },
      { floor: "deck_floor_contact", title: "Contact" },
    ].flatMap(({ floor, title }) => {
      const object = scene.getObjectByName(floor);
      if (!object) return [];
      const bounds = new THREE.Box3().setFromObject(object);
      const center = bounds.getCenter(new THREE.Vector3());
      center.y = bounds.max.y;
      center.applyMatrix4(inverse);
      center.y += HEADING_LIFT;
      return [{ title, position: center.toArray() }];
    });
  }, [scene]);
  return (
    <group name="stationIslandHeadings">
      {headings.map(({ title, position }) => (
        <Billboard key={title} position={position}>
          <StationHeading title={title} width={4.2} lightColor={lightColor} />
        </Billboard>
      ))}
    </group>
  );
}

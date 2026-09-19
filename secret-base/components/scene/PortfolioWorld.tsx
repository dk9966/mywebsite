import { Lighting } from "./Lighting";
import { CaveShell } from "./CaveShell";
import { Dust } from "./Dust";
import { Bridge } from "./Bridge";
import { ProjectsIsland } from "./ProjectsIsland";
import { AboutIsland } from "./AboutIsland";
import { WorkshopIsland } from "./WorkshopIsland";
import { ExperiencesIsland } from "./ExperiencesIsland";
import { ContactIsland } from "./ContactIsland";
import { MinecraftIsland } from "./MinecraftIsland";
import { GarageIsland } from "./GarageIsland";
import { BakedWorld } from "./BakedWorld";
import { ImportedPillar } from "./ImportedPillar";
import { islandLayout, rimPoint } from "./layout";
import { useViewStore } from "./viewStore";
import { sceneMode } from "./sceneMode";
import type { ThreeEvent } from "@react-three/fiber";
import type { Object3D } from "three";

const L = islandLayout;
const MODE = sceneMode();

// Minecraft is a voxel island, so its bridge landing is computed by hand:
// edge blocks (height 1) have their top surface ≈ 0.36 above the group origin.
function minecraftRim(): [number, number, number] {
  const [mx, my, mz] = L.minecraft.position;
  const dx = L.projects.position[0] - mx;
  const dz = L.projects.position[2] - mz;
  const len = Math.hypot(dx, dz);
  const r = 2.2;
  return [mx + (dx / len) * r, my + 0.4, mz + (dz / len) * r];
}

/** Procedural islands + bridges; wrapped in the exportable "world" group. */
function ProceduralWorld() {
  return (
    <group name="world">
      <ProjectsIsland />
      <AboutIsland />
      <WorkshopIsland />
      <ExperiencesIsland />
      <ContactIsland />
      <MinecraftIsland />
      <GarageIsland />

      {/* entrance staircase: garage platform up into Projects */}
      <Bridge
        from={rimPoint(L.garage, L.projects)}
        to={rimPoint(L.projects, L.garage)}
        lamps={2}
      />

      {/* hub connections */}
      <Bridge from={rimPoint(L.projects, L.about)} to={rimPoint(L.about, L.projects)} />
      <Bridge from={rimPoint(L.projects, L.workshop)} to={rimPoint(L.workshop, L.projects)} lamps={3} />
      <Bridge from={rimPoint(L.projects, L.experiences)} to={rimPoint(L.experiences, L.projects)} />
      <Bridge from={rimPoint(L.projects, L.contact)} to={rimPoint(L.contact, L.projects)} lamps={3} />
      <Bridge from={rimPoint(L.projects, L.minecraft)} to={minecraftRim()} lamps={2} />

      {/* optional side bridge: Workshop ↔ About */}
      <Bridge from={rimPoint(L.workshop, L.about)} to={rimPoint(L.about, L.workshop)} lamps={1} />
    </group>
  );
}

const ISLAND_VIEWS: Record<string, "projects" | "about"> = {
  projectsIsland: "projects",
  aboutIsland: "about",
};

function findIslandView(obj: Object3D | null): "projects" | "about" | null {
  while (obj) {
    const view = ISLAND_VIEWS[obj.name];
    if (view) return view;
    obj = obj.parent;
  }
  return null;
}

/** Root scene graph: background (always procedural) + the world group. */
export function PortfolioWorld() {
  const toggleView = useViewStore((s) => s.toggleView);

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    const view = findIslandView(e.object);
    if (view) {
      e.stopPropagation();
      toggleView(view);
    }
  };
  const handleOver = (e: ThreeEvent<PointerEvent>) => {
    if (findIslandView(e.object)) document.body.style.cursor = "pointer";
  };
  const handleOut = () => {
    document.body.style.cursor = "auto";
  };

  return (
    <group name="portfolioWorld">
      {MODE !== "station" && (
        <>
          <Lighting />
          <CaveShell />
          <Dust />
        </>
      )}
      <group
        // Station meshes have no island click targets. Avoid raycasting the
        // entire imported model on every pointer move over the preview.
        onClick={MODE === "station" ? undefined : handleClick}
        onPointerOver={MODE === "station" ? undefined : handleOver}
        onPointerOut={MODE === "station" ? undefined : handleOut}
      >
        {MODE === "station" ? (
          <ImportedPillar />
        ) : MODE === "procedural" ? (
          <ProceduralWorld />
        ) : (
          <BakedWorld />
        )}
      </group>
    </group>
  );
}

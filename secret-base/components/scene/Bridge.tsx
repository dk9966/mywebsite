import { useMemo } from "react";
import * as THREE from "three";
import { graphite, graphiteDark, neonCyan, lampWarm } from "./materials";

type Vec3 = [number, number, number];

const STAIR_SLOPE = 0.25; // steeper spans render as staircases

function LampPost({ position }: { position: Vec3 }) {
  return (
    <group position={position}>
      <mesh material={graphiteDark} position={[0, 0.48, 0]}>
        <boxGeometry args={[0.1, 0.96, 0.1]} />
      </mesh>
      <mesh material={lampWarm} position={[0, 1.08, 0]}>
        <boxGeometry args={[0.24, 0.3, 0.24]} />
      </mesh>
      <mesh material={graphiteDark} position={[0, 1.26, 0]}>
        <boxGeometry args={[0.3, 0.07, 0.3]} />
      </mesh>
    </group>
  );
}

/** Flat/ramp variant: chunky slab deck with planks, fascia, rails, glow. */
function RampDeck({ length, width, lamps }: { length: number; width: number; lamps: number }) {
  const plankCount = Math.max(4, Math.round(length / 0.85));
  const plankDepth = (length / plankCount) * 0.82;
  const postCount = Math.max(2, Math.round(length / 1.25));
  const fasciaX = width / 2 + 0.09;
  const railX = width / 2 - 0.1;

  return (
    <group>
      {/* solid slab */}
      <mesh material={graphiteDark} position={[0, -0.12, 0]}>
        <boxGeometry args={[width, 0.2, length]} />
      </mesh>
      {/* side fascia, slightly proud of the deck */}
      {[fasciaX, -fasciaX].map((x) => (
        <mesh key={x} material={graphiteDark} position={[x, -0.08, 0]}>
          <boxGeometry args={[0.16, 0.36, length]} />
        </mesh>
      ))}
      {/* planks */}
      {Array.from({ length: plankCount }, (_, i) => (
        <mesh
          key={i}
          material={graphite}
          position={[0, 0.02, -length / 2 + ((i + 0.5) * length) / plankCount]}
        >
          <boxGeometry args={[width - 0.02, 0.08, plankDepth]} />
        </mesh>
      ))}
      {/* continuous cyan edge strips on top of the fascia (outside the rails) */}
      {[fasciaX, -fasciaX].map((x) => (
        <mesh key={`n${x}`} material={neonCyan} position={[x, 0.13, 0]}>
          <boxGeometry args={[0.09, 0.06, length]} />
        </mesh>
      ))}
      {/* railings, inset so they don't chop the glow line */}
      {[railX, -railX].map((x) => (
        <group key={`r${x}`}>
          <mesh material={graphite} position={[x, 0.6, 0]}>
            <boxGeometry args={[0.08, 0.09, length * 0.98]} />
          </mesh>
          <mesh material={graphiteDark} position={[x, 0.34, 0]}>
            <boxGeometry args={[0.05, 0.05, length * 0.98]} />
          </mesh>
          {Array.from({ length: postCount + 1 }, (_, i) => (
            <mesh
              key={i}
              material={graphiteDark}
              position={[x, 0.28, -length / 2 + (i * length) / postCount]}
            >
              <boxGeometry args={[0.09, 0.56, 0.09]} />
            </mesh>
          ))}
        </group>
      ))}
      {/* lamp posts on the fascia */}
      {Array.from({ length: lamps }, (_, i) => {
        const t = (i + 1) / (lamps + 1);
        const x = (i % 2 === 0 ? 1 : -1) * fasciaX;
        return <LampPost key={i} position={[x, 0.1, -length / 2 + t * length]} />;
      })}
      {/* chunky end pylons with glowing caps */}
      {[length / 2 - 0.12, -length / 2 + 0.12].map((z) =>
        [fasciaX, -fasciaX].map((x) => (
          <group key={`${z}${x}`} position={[x, 0, z]}>
            <mesh material={graphiteDark} position={[0, 0.38, 0]}>
              <boxGeometry args={[0.2, 0.8, 0.2]} />
            </mesh>
            <mesh material={neonCyan} position={[0, 0.82, 0]}>
              <boxGeometry args={[0.14, 0.08, 0.14]} />
            </mesh>
          </group>
        )),
      )}
      {/* longitudinal under-deck beams */}
      {[width / 3, -width / 3].map((x) => (
        <mesh key={`b${x}`} material={graphiteDark} position={[x, -0.27, 0]}>
          <boxGeometry args={[0.12, 0.16, length * 0.94]} />
        </mesh>
      ))}
      {/* trestle supports + X bracing under long spans */}
      {length > 6.5 &&
        [-length / 4, length / 4].map((z) => (
          <group key={z} position={[0, 0, z]}>
            {[width / 3, -width / 3].map((x) => (
              <mesh key={x} material={graphiteDark} position={[x, -1.2, 0]}>
                <boxGeometry args={[0.16, 2.1, 0.16]} />
              </mesh>
            ))}
            <mesh material={graphiteDark} position={[0, -0.55, 0]}>
              <boxGeometry args={[width * 0.85, 0.14, 0.14]} />
            </mesh>
            {[0.6, -0.6].map((r) => (
              <mesh
                key={r}
                material={graphiteDark}
                position={[0, -1.35, 0]}
                rotation={[0, 0, r]}
              >
                <boxGeometry args={[width * 0.95, 0.07, 0.07]} />
              </mesh>
            ))}
          </group>
        ))}
    </group>
  );
}

/** Staircase variant: horizontal steps descending, glowing stringers. */
function Stairs({
  horizontal,
  drop,
  width,
  lamps,
}: {
  horizontal: number;
  drop: number; // signed: to.y - from.y
  width: number;
  lamps: number;
}) {
  const stepCount = Math.max(5, Math.round(horizontal / 0.55));
  const stepDepth = horizontal / stepCount;
  const slopeLen = Math.hypot(horizontal, drop);
  const pitch = Math.atan2(drop, horizontal);
  const fasciaX = width / 2 + 0.07;

  const steps = Array.from({ length: stepCount }, (_, i) => ({
    z: (i + 0.5) * stepDepth,
    y: (i + 0.5) * (drop / stepCount),
  }));

  const railX = width / 2 - 0.06;

  return (
    <group>
      {steps.map(({ z, y }, i) => (
        <group key={i}>
          <mesh material={graphite} position={[0, y - 0.05, z]}>
            <boxGeometry args={[width, 0.1, stepDepth * 1.04]} />
          </mesh>
          <mesh material={graphiteDark} position={[0, y - 0.22, z]}>
            <boxGeometry args={[width * 0.9, 0.26, stepDepth * 0.9]} />
          </mesh>
          {/* railing posts every other step */}
          {i % 2 === 0 &&
            [railX, -railX].map((x) => (
              <mesh
                key={x}
                material={graphiteDark}
                position={[x, y + 0.26, z]}
              >
                <boxGeometry args={[0.07, 0.52, 0.07]} />
              </mesh>
            ))}
        </group>
      ))}
      {/* sloped handrails above the posts */}
      {[railX, -railX].map((x) => (
        <group
          key={`hr${x}`}
          position={[x, drop / 2 + 0.55, horizontal / 2]}
          rotation={[-pitch, 0, 0]}
        >
          <mesh material={graphite}>
            <boxGeometry args={[0.06, 0.07, slopeLen * 0.98]} />
          </mesh>
        </group>
      ))}
      {/* sloped stringers with cyan strips */}
      {[fasciaX, -fasciaX].map((x) => (
        <group
          key={x}
          position={[x, drop / 2 - 0.14, horizontal / 2]}
          rotation={[-pitch, 0, 0]}
        >
          <mesh material={graphiteDark}>
            <boxGeometry args={[0.14, 0.34, slopeLen]} />
          </mesh>
          <mesh material={neonCyan} position={[0, 0.2, 0]}>
            <boxGeometry args={[0.08, 0.06, slopeLen]} />
          </mesh>
        </group>
      ))}
      {/* occasional lamps along the stringers */}
      {Array.from({ length: lamps }, (_, i) => {
        const t = (i + 1) / (lamps + 1);
        const x = (i % 2 === 0 ? 1 : -1) * fasciaX;
        return (
          <LampPost key={i} position={[x, drop * t + 0.06, horizontal * t]} />
        );
      })}
    </group>
  );
}

/**
 * Modular bridge between two points. Gentle spans render as plank ramps;
 * steep spans automatically become staircases (like the reference).
 */
export function Bridge({
  from,
  to,
  width = 1.6,
  lamps = 2,
}: {
  from: Vec3;
  to: Vec3;
  width?: number;
  lamps?: number;
}) {
  const geo = useMemo(() => {
    const a = new THREE.Vector3(...from);
    const b = new THREE.Vector3(...to);
    const dir = b.clone().sub(a);
    const length = dir.length();
    const horizontal = Math.hypot(dir.x, dir.z);
    const drop = dir.y;
    const slope = horizontal > 0 ? Math.abs(drop) / horizontal : 0;
    const yaw = Math.atan2(dir.x, dir.z);
    const quaternion = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, 0, 1),
      dir.clone().normalize(),
    );
    const mid = a.clone().add(b).multiplyScalar(0.5);
    return { a, mid, quaternion, length, horizontal, drop, slope, yaw };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...from, ...to]);

  if (geo.slope > STAIR_SLOPE) {
    // stairs are built in an unrotated (yaw-only) frame starting at `from`
    return (
      <group
        position={[geo.a.x, geo.a.y, geo.a.z]}
        rotation={[0, geo.yaw, 0]}
        name="bridgeStairs"
      >
        <Stairs
          horizontal={geo.horizontal}
          drop={geo.drop}
          width={width}
          lamps={lamps}
        />
      </group>
    );
  }

  return (
    <group
      position={[geo.mid.x, geo.mid.y, geo.mid.z]}
      quaternion={geo.quaternion}
      name="bridge"
    >
      <RampDeck length={geo.length} width={width} lamps={lamps} />
    </group>
  );
}

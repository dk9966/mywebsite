import type { ReactNode } from "react";
import {
  graphite,
  graphiteDark,
  neonCyan,
  neonCyanFaint,
  rock,
  rockDark,
} from "./materials";

type Point = readonly [tangent: number, vertical: number];

const CHANNEL_PATTERNS: readonly (readonly Point[])[] = [
  [
    [-0.24, 0.48],
    [-0.24, 0.26],
    [0.12, 0.13],
    [0.12, -0.1],
    [-0.14, -0.24],
    [-0.14, -0.48],
  ],
  [
    [0.18, 0.46],
    [0.18, 0.18],
    [-0.2, 0.01],
    [-0.2, -0.19],
    [0.08, -0.32],
    [0.08, -0.46],
  ],
  [
    [-0.08, 0.47],
    [-0.08, 0.31],
    [0.24, 0.16],
    [0.24, -0.09],
    [-0.22, -0.27],
    [-0.22, -0.45],
  ],
  [
    [0.26, 0.44],
    [-0.08, 0.28],
    [-0.08, 0.02],
    [0.17, -0.11],
    [0.17, -0.31],
    [-0.16, -0.46],
  ],
];

function RadialSegment({
  radius,
  y1,
  y2,
  z1,
  z2,
  depth,
  width,
  material,
}: {
  radius: number;
  y1: number;
  y2: number;
  z1: number;
  z2: number;
  depth: number;
  width: number;
  material: typeof graphiteDark;
}) {
  const dy = y2 - y1;
  const dz = z2 - z1;
  const length = Math.hypot(dy, dz);

  return (
    <mesh
      material={material}
      position={[radius, (y1 + y2) / 2, (z1 + z2) / 2]}
      rotation={[Math.atan2(dz, dy), 0, 0]}
    >
      <boxGeometry args={[depth, length, width]} />
    </mesh>
  );
}

function Channel({
  angle,
  radius,
  centerY,
  height,
  panelWidth,
  variant,
}: {
  angle: number;
  radius: number;
  centerY: number;
  height: number;
  panelWidth: number;
  variant: number;
}) {
  const points = CHANNEL_PATTERNS[variant % CHANNEL_PATTERNS.length];
  const segments: ReactNode[] = [];

  for (let i = 1; i < points.length; i += 1) {
    const [z1, y1] = points[i - 1];
    const [z2, y2] = points[i];
    const segment = {
      y1: centerY + y1 * height,
      y2: centerY + y2 * height,
      z1: z1 * panelWidth,
      z2: z2 * panelWidth,
    };

    segments.push(
      <RadialSegment
        key={`groove-${i}`}
        {...segment}
        radius={radius}
        depth={0.055}
        width={0.16}
        material={rockDark}
      />,
      <RadialSegment
        key={`light-${i}`}
        {...segment}
        radius={radius + 0.035}
        depth={0.035}
        width={0.045}
        material={neonCyanFaint}
      />,
    );
  }

  return <group rotation={[0, angle, 0]}>{segments}</group>;
}

function SlantedRecess({
  angle,
  radius,
  centerY,
  panelWidth,
  index,
}: {
  angle: number;
  radius: number;
  centerY: number;
  panelWidth: number;
  index: number;
}) {
  const direction = index % 2 === 0 ? 1 : -1;
  const length = 0.3 + (index % 3) * 0.09;
  const yOffset = ((index * 7) % 5 - 2) * 0.72;

  return (
    <group rotation={[0, angle, 0]}>
      <RadialSegment
        radius={radius}
        y1={centerY + yOffset - length}
        y2={centerY + yOffset + length}
        z1={-direction * panelWidth * 0.22}
        z2={direction * panelWidth * 0.22}
        depth={0.045}
        width={0.09}
        material={rockDark}
      />
    </group>
  );
}

/**
 * A faceted sci-fi support column: broad cap, subtly waisted shaft, angular
 * armor panels, irregular recessed circuit channels, and a stepped footing.
 */
export function MechanicalPillar({
  radius,
  depth,
  segments,
}: {
  radius: number;
  depth: number;
  segments: number;
}) {
  const sides = Math.max(12, segments * 2);
  const topY = -1.72;
  const groundY = -depth;
  const capHeight = 1.05;
  const baseHeight = 2.3;
  const shaftTop = topY - capHeight;
  const shaftBottom = groundY + baseHeight;
  const shaftHeight = shaftTop - shaftBottom;
  const shoulderHeight = Math.min(2.7, shaftHeight * 0.16);
  const centerHeight = shaftHeight - shoulderHeight * 2;
  const topRadius = radius * 0.61;
  const waistRadius = radius * 0.47;
  const bottomRadius = radius * 0.66;
  const panelDepth = Math.max(0.08, radius * 0.025);
  const panelWidth =
    2 * waistRadius * Math.tan(Math.PI / sides) * 0.76;

  const panels = Array.from({ length: sides }, (_, i) => {
    const angle = (i / sides) * Math.PI * 2;
    const topPanelHeight = shoulderHeight * (0.78 + ((i * 5) % 4) * 0.045);
    const centerPanelHeight = centerHeight * (0.9 + ((i * 7) % 3) * 0.025);
    const bottomPanelHeight =
      shoulderHeight * (0.76 + ((i * 3) % 5) * 0.035);
    const material = i % 5 === 0 ? graphite : graphiteDark;
    const radialNudge = ((i * 11) % 3) * panelDepth * 0.2;

    return (
      <group key={`panel-${i}`} rotation={[0, angle, 0]}>
        <mesh
          material={material}
          position={[
            (topRadius + waistRadius) / 2 + panelDepth / 2 + radialNudge,
            shaftTop - shoulderHeight / 2,
            0,
          ]}
          rotation={[0, 0, i % 3 === 0 ? 0.025 : -0.012]}
        >
          <boxGeometry
            args={[panelDepth, topPanelHeight, panelWidth * (0.86 + (i % 2) * 0.08)]}
          />
        </mesh>
        <mesh
          material={material}
          position={[
            waistRadius + panelDepth / 2 + radialNudge,
            shaftBottom + shoulderHeight + centerHeight / 2,
            0,
          ]}
        >
          <boxGeometry
            args={[panelDepth, centerPanelHeight, panelWidth * (0.9 + (i % 3) * 0.035)]}
          />
        </mesh>
        <mesh
          material={material}
          position={[
            (bottomRadius + waistRadius) / 2 + panelDepth / 2 + radialNudge,
            shaftBottom + shoulderHeight / 2,
            0,
          ]}
          rotation={[0, 0, i % 4 === 0 ? -0.03 : 0.01]}
        >
          <boxGeometry
            args={[panelDepth, bottomPanelHeight, panelWidth * (0.84 + (i % 3) * 0.06)]}
          />
        </mesh>
      </group>
    );
  });

  const channels = Array.from({ length: Math.ceil(sides / 2) }, (_, i) => {
    const facet = i * 2 + (i % 3 === 0 ? 1 : 0);
    const angle = ((facet + 0.5) / sides) * Math.PI * 2;

    return (
      <Channel
        key={`channel-${i}`}
        angle={angle}
        radius={waistRadius + panelDepth + 0.015}
        centerY={shaftBottom + shoulderHeight + centerHeight / 2}
        height={centerHeight * (0.82 + (i % 3) * 0.04)}
        panelWidth={panelWidth}
        variant={i}
      />
    );
  });

  const recesses = Array.from({ length: Math.floor(sides / 2) }, (_, i) => {
    const facet = i * 2;
    return (
      <SlantedRecess
        key={`recess-${i}`}
        angle={((facet + 0.5) / sides) * Math.PI * 2}
        radius={waistRadius + panelDepth + 0.01}
        centerY={shaftBottom + shoulderHeight + centerHeight / 2}
        panelWidth={panelWidth}
        index={i}
      />
    );
  });

  return (
    <group name="mechanicalPillar">
      {/* flat top disk and stepped shoulder beneath the island deck */}
      <mesh material={graphite} position={[0, topY - 0.16, 0]}>
        <cylinderGeometry args={[radius * 0.76, radius * 0.72, 0.32, sides]} />
      </mesh>
      <mesh material={graphiteDark} position={[0, topY - 0.43, 0]}>
        <cylinderGeometry args={[radius * 0.7, radius * 0.66, 0.22, sides]} />
      </mesh>
      <mesh material={rock} position={[0, topY - 0.76, 0]}>
        <cylinderGeometry args={[radius * 0.65, topRadius, 0.48, sides]} />
      </mesh>
      <mesh
        material={neonCyan}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, topY - 0.55, 0]}
      >
        <torusGeometry args={[radius * 0.655, 0.035, 4, sides]} />
      </mesh>

      {/* three-part shaft gives the column its restrained hourglass profile */}
      <mesh
        material={rockDark}
        position={[0, shaftTop - shoulderHeight / 2, 0]}
      >
        <cylinderGeometry
          args={[topRadius, waistRadius, shoulderHeight, sides]}
        />
      </mesh>
      <mesh
        material={rockDark}
        position={[
          0,
          shaftBottom + shoulderHeight + centerHeight / 2,
          0,
        ]}
      >
        <cylinderGeometry
          args={[waistRadius, waistRadius, centerHeight, sides]}
        />
      </mesh>
      <mesh
        material={rockDark}
        position={[0, shaftBottom + shoulderHeight / 2, 0]}
      >
        <cylinderGeometry
          args={[waistRadius, bottomRadius, shoulderHeight, sides]}
        />
      </mesh>

      {panels}
      {recesses}
      {channels}

      {/* stepped mechanical footing with deliberately uneven perimeter blocks */}
      <mesh material={rock} position={[0, groundY + 1.72, 0]}>
        <cylinderGeometry
          args={[radius * 0.68, radius * 0.76, 0.48, sides]}
        />
      </mesh>
      <mesh material={graphiteDark} position={[0, groundY + 1.25, 0]}>
        <cylinderGeometry
          args={[radius * 0.79, radius * 0.86, 0.48, sides]}
        />
      </mesh>
      <mesh material={rock} position={[0, groundY + 0.76, 0]}>
        <cylinderGeometry
          args={[radius * 0.88, radius * 0.98, 0.5, sides]}
        />
      </mesh>
      <mesh material={graphiteDark} position={[0, groundY + 0.25, 0]}>
        <cylinderGeometry
          args={[radius * 1.02, radius * 1.08, 0.5, sides]}
        />
      </mesh>
      {Array.from({ length: sides }, (_, i) => {
        const angle = ((i + 0.5) / sides) * Math.PI * 2;
        const protrusion = radius * (1.01 + ((i * 7) % 4) * 0.025);
        const blockHeight = 0.2 + (i % 3) * 0.08;

        return (
          <group key={`foot-block-${i}`} rotation={[0, angle, 0]}>
            <mesh
              material={i % 4 === 0 ? graphite : rock}
              position={[protrusion, groundY + 0.48 + blockHeight / 2, 0]}
            >
              <boxGeometry
                args={[
                  radius * (0.12 + (i % 2) * 0.025),
                  blockHeight,
                  panelWidth * (0.92 + (i % 3) * 0.08),
                ]}
              />
            </mesh>
          </group>
        );
      })}
      <mesh
        material={neonCyanFaint}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, groundY + 1.5, 0]}
      >
        <torusGeometry args={[radius * 0.79, 0.035, 4, sides]} />
      </mesh>
    </group>
  );
}

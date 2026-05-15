import { useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import { tronLinesFromGLB } from "../lib/tronLinesFromGLB";
import TronGrid from "./TronGrid";

const TABLE_GLB_URL = "/models/table.glb";

useGLTF.preload(TABLE_GLB_URL);

// The GLB carries the desk geometry *plus* the authored TronLine_* polylines.
// We load it only to extract waypoints — none of the meshes enter the React
// scene graph. The final visual is just the animated lines on pure black, and
// when they all settle the table reads as a Tron-lines silhouette.
export default function TronTable() {
  const { scene } = useGLTF(TABLE_GLB_URL);
  const paths = useMemo(() => tronLinesFromGLB(scene), [scene]);
  return <TronGrid paths={paths} showBackgroundGrid={false} />;
}

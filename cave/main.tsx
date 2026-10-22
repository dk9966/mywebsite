import { createRoot, type Root } from "react-dom/client";
import CaveApp from "../secret-base/CaveApp";

// Vite can re-evaluate this entry during edits. Reuse the React root rather
// than leaving competing Canvas/WebGL roots attached to the same container.
const root = (import.meta.hot?.data.root as Root | undefined)
  ?? createRoot(document.getElementById("root")!);
if (import.meta.hot) import.meta.hot.data.root = root;
// No StrictMode: it runs every effect twice in development, and the cave's
// effects are GPU builds (shadow maps, the composer, shader pipelines) and a
// Voxelize connection — several seconds of load for nothing.
root.render(<CaveApp />);

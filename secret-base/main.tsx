import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import App from "./App";

// Vite can re-evaluate this entry during edits. Reuse the React root rather
// than leaving competing Canvas/WebGL roots attached to the same container.
const root = (import.meta.hot?.data.root as Root | undefined)
  ?? createRoot(document.getElementById("root")!);
if (import.meta.hot) import.meta.hot.data.root = root;
root.render(
  <StrictMode>
    <App />
  </StrictMode>,
);

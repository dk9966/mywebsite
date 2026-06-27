import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Circuit3DEditor from "./components/Circuit3DEditor";
import { useCircuitEditShortcuts } from "./hooks/useCircuitEditShortcuts";

function App() {
  useCircuitEditShortcuts();
  return <Circuit3DEditor />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import TextLab from "./TextLab";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TextLab />
  </StrictMode>,
);

import { useEffect } from "react";
import { useThree } from "@react-three/fiber";

function bufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

declare global {
  interface Window {
    __exportWorld?: (opts?: { download?: boolean }) => Promise<string | null>;
  }
}

/**
 * Dev-only: registers window.__exportWorld().
 * - `__exportWorld({ download: true })` downloads world.glb in the browser.
 * - `__exportWorld()` returns the GLB as base64 (used by the export script).
 * Exports the group named "world" — islands + bridges, no cave background.
 */
export function DevExport() {
  const scene = useThree((s) => s.scene);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    window.__exportWorld = async (opts) => {
      const world = scene.getObjectByName("world");
      if (!world) {
        console.warn("__exportWorld: no group named 'world' found");
        return null;
      }
      const { GLTFExporter } = await import(
        "three/addons/exporters/GLTFExporter.js"
      );
      const exporter = new GLTFExporter();
      const result = (await exporter.parseAsync(world, {
        binary: true,
      })) as ArrayBuffer;
      if (opts?.download) {
        const blob = new Blob([result], { type: "model/gltf-binary" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "world.glb";
        a.click();
        URL.revokeObjectURL(a.href);
        return null;
      }
      return bufferToBase64(result);
    };
    return () => {
      delete window.__exportWorld;
    };
  }, [scene]);

  return null;
}

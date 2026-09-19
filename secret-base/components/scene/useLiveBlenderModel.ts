import { useEffect, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// Capture owned resources before the scene receives shared website materials.
function ownedResources(scene: THREE.Object3D) {
  const resources = new Set<{ dispose(): void }>();
  scene.traverse(object => {
    const mesh = object as THREE.Mesh;
    if (mesh.geometry) resources.add(mesh.geometry);
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) {
      if (!material) continue;
      resources.add(material);
      for (const value of Object.values(material)) {
        if (value instanceof THREE.Texture) resources.add(value);
      }
    }
  });
  return () => resources.forEach(resource => resource.dispose());
}

export function useLiveBlenderModel(url: string, model: 'pillar' | 'world') {
  const [loaded, setLoaded] = useState<{ scene: THREE.Group; dispose(): void } | null>(null);

  useEffect(() => {
    let stopped = false;
    let version: string | undefined;
    let hasModel = false;
    let refreshing = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const loader = new GLTFLoader();

    async function refresh() {
      if (refreshing || stopped) return;
      refreshing = true;
      let nextVersion = version;
      try {
        // Background previews should not poll or parse newly exported models.
        if (document.hidden) return;
        if (import.meta.env.DEV) {
          const response = await fetch(`/__blender-live?model=${model}`, {
            cache: 'no-store', signal: controller.signal,
          });
          if (!response.ok) throw new Error(`Model status: ${response.status}`);
          nextVersion = (await response.json()).version;
        }
        if (!hasModel || nextVersion !== version) {
          const asset = new URL(url, window.location.href);
          if (nextVersion) asset.searchParams.set('blenderVersion', nextVersion);
          const gltf = await loader.loadAsync(asset.href);
          const dispose = ownedResources(gltf.scene);
          if (stopped) { dispose(); return; }
          setLoaded({ scene: gltf.scene, dispose });
          hasModel = true;
          version = nextVersion;
        }
      } catch (error) {
        if (!stopped) console.warn('[Blender live] Keeping previous mesh; will retry.', error);
      } finally {
        refreshing = false;
        if (!stopped && !document.hidden && (import.meta.env.DEV || !hasModel)) timer = setTimeout(refresh, 1500);
      }
    }
    const onVisibility = () => {
      if (document.hidden) clearTimeout(timer);
      else { clearTimeout(timer); void refresh(); }
    };
    document.addEventListener('visibilitychange', onVisibility);
    void refresh();
    return () => {
      stopped = true;
      controller.abort();
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [url, model]);

  // Runs after React replaces the old primitive. Shared website materials survive.
  useEffect(() => () => loaded?.dispose(), [loaded]);
  return loaded?.scene ?? null;
}

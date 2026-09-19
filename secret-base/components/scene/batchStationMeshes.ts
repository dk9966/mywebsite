import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** Batch nearby static opaque pieces while retaining the named Blender hierarchy. */
export function batchStationMeshes(scene: THREE.Object3D) {
  scene.updateWorldMatrix(true, true);
  const inverse = scene.matrixWorld.clone().invert();
  const buckets = new Map<string, { mesh: THREE.Mesh; matrix: THREE.Matrix4 }[]>();
  scene.traverseVisible((object) => {
    if (!(object instanceof THREE.Mesh) || object instanceof THREE.SkinnedMesh ||
      object instanceof THREE.InstancedMesh || Array.isArray(object.material)) return;
    const geometry: THREE.BufferGeometry = object.geometry;
    const material: THREE.Material = object.material;
    if (material.transparent || !material.visible || object.morphTargetInfluences?.length ||
      Object.keys(geometry.morphAttributes).length || geometry.groups.length > 1 ||
      geometry.drawRange.start !== 0 || geometry.drawRange.count !== Infinity ||
      object.onBeforeRender !== THREE.Object3D.prototype.onBeforeRender ||
      object.onAfterRender !== THREE.Object3D.prototype.onAfterRender) return;
    const matrix = inverse.clone().multiply(object.matrixWorld);
    // Mirrored transforms need winding correction; leave those meshes untouched.
    if (matrix.determinant() <= 0) return;
    geometry.computeBoundingBox();
    const center = geometry.boundingBox!.getCenter(new THREE.Vector3()).applyMatrix4(matrix);
    const cell = center.toArray().map(value => Math.floor(value / 6)).join(",");
    const attributes = Object.entries(geometry.attributes).map(([name, attr]) =>
      `${name}:${attr.itemSize}:${attr.normalized}:${attr.array.constructor.name}`).sort().join(";");
    const key = [material.uuid, cell, attributes, !!geometry.index, object.layers.mask,
      object.renderOrder, object.castShadow, object.receiveShadow, object.frustumCulled].join("|");
    const bucket = buckets.get(key) ?? [];
    bucket.push({ mesh: object, matrix });
    buckets.set(key, bucket);
  });
  const batches: THREE.Mesh[] = [];
  const originals: { mesh: THREE.Mesh; mask: number }[] = [];
  for (const entries of buckets.values()) {
    if (entries.length < 2) continue;
    const parts = entries.map(({ mesh, matrix }) => mesh.geometry.clone().applyMatrix4(matrix));
    const geometry = mergeGeometries(parts, false);
    parts.forEach(part => part.dispose());
    if (!geometry) continue;
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    const source = entries[0].mesh;
    const batch = new THREE.Mesh(geometry, source.material);
    batch.name = `station_batch_${batches.length}`;
    batch.layers.mask = source.layers.mask;
    batch.renderOrder = source.renderOrder;
    batch.castShadow = source.castShadow;
    batch.receiveShadow = source.receiveShadow;
    batch.frustumCulled = source.frustumCulled;
    batch.matrixAutoUpdate = false;
    // Layers hide only the mesh, so its child fixtures still render normally.
    for (const { mesh } of entries) {
      originals.push({ mesh, mask: mesh.layers.mask });
      mesh.layers.mask = 0;
    }
    scene.add(batch);
    batches.push(batch);
  }
  return {
    sourceMeshes: originals.length,
    batches: batches.length,
    dispose() {
      originals.forEach(({ mesh, mask }) => { mesh.layers.mask = mask; });
      batches.forEach(batch => { scene.remove(batch); batch.geometry.dispose(); });
    },
  };
}

import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { batchStationMeshes } from '../secret-base/components/scene/batchStationMeshes';
const data = readFileSync('secret-base/models/pillar.glb');
const gltf = await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength), '');
const scene = gltf.scene;
function stats() {
  let draws=0, triangles=0; const box=new THREE.Box3();
  scene.updateWorldMatrix(true,true);
  scene.traverseVisible(o => {
    if (!(o instanceof THREE.Mesh) || !(o.layers.mask & 1)) return;
    draws++; triangles+=(o.geometry.index?.count ?? o.geometry.attributes.position.count)/3;
    const position=o.geometry.attributes.position;
    for(let i=0;i<position.count;i++) box.expandByPoint(new THREE.Vector3().fromBufferAttribute(position,i).applyMatrix4(o.matrixWorld));
  });
  return {draws,triangles,box};
}
const before=stats(); const batch=batchStationMeshes(scene); const after=stats();
assert.equal(after.triangles,before.triangles);
assert.ok(after.box.min.distanceTo(before.box.min)<1e-5);
assert.ok(after.box.max.distanceTo(before.box.max)<1e-5);
assert.ok(after.draws<before.draws);
batch.dispose(); assert.equal(stats().draws,before.draws);
const again=batchStationMeshes(scene); assert.equal(stats().draws,after.draws); again.dispose();
console.log(JSON.stringify({before:before.draws,after:after.draws,triangles:after.triangles,batches:batch.batches,batchedMeshes:batch.sourceMeshes,cleanup:'passed'},null,2));

// Transparent fixtures and mirrored pieces retain their own draw calls.
const fixtureScene = new THREE.Group();
const parent = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial());
parent.geometry.clearGroups();
const sibling = new THREE.Mesh(parent.geometry, parent.material); sibling.position.x=2;
const glass = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial({transparent:true,opacity:0.5}));
parent.add(glass); fixtureScene.add(parent,sibling);
const fixtureBatch=batchStationMeshes(fixtureScene);
assert.equal(fixtureBatch.sourceMeshes,2);
assert.equal(parent.layers.mask,0);
assert.equal(glass.layers.mask,1);
assert.equal(glass.parent,parent);
fixtureBatch.dispose();
assert.equal(parent.layers.mask,1);
sibling.scale.x=-1;
const mirrored=batchStationMeshes(fixtureScene);
assert.equal(mirrored.sourceMeshes,0);
mirrored.dispose();
console.log('Transparent child and mirrored-transform checks passed.');

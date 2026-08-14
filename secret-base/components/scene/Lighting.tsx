/** Simple Phase 1 lighting: hemisphere + key/fill + a few accent points. */
export function Lighting() {
  return (
    <group name="lighting">
      <ambientLight intensity={0.3} color="#3a5aa8" />
      <hemisphereLight args={["#4a6da3", "#0c1226", 1.7]} />
      <directionalLight position={[14, 20, 12]} intensity={2.6} color="#c3d8ff" />
      <directionalLight position={[-12, 8, -8]} intensity={0.55} color="#3a6aff" />
      {/* crystal glow on Projects */}
      <pointLight position={[0, 3.2, 0]} intensity={26} distance={16} color="#57c8ff" />
      {/* warm workshop light */}
      <pointLight position={[-12.4, 1.6, 5.4]} intensity={14} distance={9} color="#ffb254" />
      {/* purple contact accent */}
      <pointLight position={[15.5, 3, 2.3]} intensity={10} distance={8} color="#9a5cff" />
    </group>
  );
}

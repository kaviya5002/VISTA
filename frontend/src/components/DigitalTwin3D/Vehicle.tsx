/**
 * Vehicle — renders the holographic wireframe SUV at the Digital Twin center.
 * Uses VehicleWireframe (procedural geometry) — no GLTF dependency.
 */
import VehicleWireframe from "./VehicleWireframe";

export { VehicleWireframe as ProceduralCar };

export default function Vehicle({ isOverview = true }: { isOverview?: boolean }) {
  void isOverview;
  return <VehicleWireframe />;
}

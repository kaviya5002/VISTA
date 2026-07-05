/**
 * VehicleScene — the Three.js canvas that hosts the interactive vehicle.
 *
 * Props:
 *   twin       — component twin payload from /digital_twin/component/:id
 *   forecastTwin — optional forecast override (when slider is moved)
 *   onSelect   — fires when the user clicks a part
 *   selected   — currently selected part key
 */

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, ContactShadows } from "@react-three/drei";
import VehicleModel from "./VehicleModel";
import type { ComponentKey } from "./utils";

interface Props {
  twin:         Record<string, any> | null;
  forecastTwin: Record<string, any> | null;
  selected:     ComponentKey | null;
  onSelect:     (id: ComponentKey) => void;
}

export default function VehicleScene({ twin, forecastTwin, selected, onSelect }: Props) {
  const activeTwin = forecastTwin ?? twin;

  return (
    <div style={{ width: "100%", height: 360, borderRadius: 14, overflow: "hidden", background: "#0a0f1e" }}>
      <Canvas
        camera={{ position: [3.5, 2.2, 3.5], fov: 45 }}
        shadows
        gl={{ antialias: true }}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 8, 5]} intensity={1.2} castShadow />
        <pointLight position={[-4, 3, -4]} intensity={0.4} color="#60a5fa" />

        <Suspense fallback={null}>
          <Environment preset="city" />
          {activeTwin && (
            <VehicleModel
              twin={activeTwin}
              selected={selected}
              onSelect={onSelect}
            />
          )}
          <ContactShadows
            position={[0, -0.32, 0]}
            opacity={0.5}
            scale={5}
            blur={2}
          />
        </Suspense>

        <OrbitControls
          enablePan={false}
          minDistance={2.5}
          maxDistance={7}
          minPolarAngle={0.3}
          maxPolarAngle={Math.PI / 2.1}
          autoRotate={!selected}
          autoRotateSpeed={0.6}
        />
      </Canvas>

      {!activeTwin && (
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "#475569", fontSize: 14,
        }}>
          Loading 3D twin…
        </div>
      )}
    </div>
  );
}

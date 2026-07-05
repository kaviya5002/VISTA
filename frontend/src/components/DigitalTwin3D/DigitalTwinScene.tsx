/**
 * DigitalTwinScene — industrial holographic Digital Twin.
 *
 * Layout:
 *   - Car centered, scaled to fill ~60% of view
 *   - 6 component models in fixed positions around the car
 *   - Thin glowing lines from each component to its hotspot on the car
 *   - Compact labels on each component
 *   - Popup appears on click (fixed overlay, top-right)
 *   - No floating, no bouncing, no random motion
 *   - User OrbitControls only
 */
import { Suspense, memo, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { Grid } from "@react-three/drei";
import { BACKGROUND } from "./WireframeMaterial";
import SceneLights from "./SceneLights";
import CameraControls from "./CameraControls";
import CameraController from "./CameraController";
import { useTwinAnimation } from "./useTwinAnimation";
import type { TwinData } from "./useTwinAnimation";
import Vehicle from "./Vehicle";
import Hotspot from "./Hotspot";
import ComponentModel from "./ComponentModel";
import ConnectionBeam from "./ConnectionBeam";
import GlowEffects from "./GlowEffects";
import BackgroundParticles from "./BackgroundParticles";
import StatusRing from "./StatusRing";
import ComponentPopup from "./ComponentPopup";
import DigitalHUDOverlay from "./DigitalHUDOverlay";
import AnimatedGrid from "./AnimatedGrid";
import { REGISTRY } from "./ComponentRegistry";
import type { CameraMode } from "./useTwinAnimation";
import * as THREE from "three";

interface Props {
  twinData:            TwinData | null;
  timelineTwinData?:   TwinData | null;
  showLabels?:         boolean;
  showParticles?:      boolean;
  cameraMode?:         CameraMode;
  onCameraModeChange?: (mode: CameraMode) => void;
}

interface SceneProps {
  activeData:        TwinData;
  cameraMode:        CameraMode;
  hoveredComponent:  string | null;
  selectedComponent: string | null;
  pulseTime:         number;
  colors:            Record<string, THREE.Color>;
  showParticles:     boolean;
  onHover:           (n: string | null) => void;
  onSelect:          (n: string | null) => void;
  onComponentClick:  (n: string) => void;
  criticalCount:     number;
}

const InnerScene = memo(function InnerScene({
  activeData, cameraMode, hoveredComponent, selectedComponent,
  pulseTime, colors, showParticles,
  onHover, onSelect, onComponentClick, criticalCount,
}: SceneProps) {
  const selDef    = selectedComponent ? REGISTRY.find(c => c.name === selectedComponent) : null;
  const popupComp = selDef ? (activeData as any)[selDef.id] : null;
  const popupColor = selDef ? colors[selDef.id] : null;

  const failureProbs = useMemo(() => ({
    battery:      activeData.battery.failure_probability,
    motor:        activeData.motor.failure_probability,
    cooling:      activeData.cooling.failure_probability,
    brakes:       activeData.brakes.failure_probability,
    electrical:   activeData.electrical.failure_probability,
    transmission: activeData.transmission.failure_probability,
  }), [
    activeData.battery.failure_probability,
    activeData.motor.failure_probability,
    activeData.cooling.failure_probability,
    activeData.brakes.failure_probability,
    activeData.electrical.failure_probability,
    activeData.transmission.failure_probability,
  ]);

  return (
    <>
      <SceneLights vehicleHealth={activeData.vehicle_health} />
      <CameraController mode={cameraMode} criticalCount={criticalCount} />

      <Suspense fallback={null}>
        {/* ── Hero vehicle — centered, stable ── */}
        <Vehicle isOverview={false} />

        {/* ── Status ring around vehicle base ── */}
        <StatusRing health={activeData.vehicle_health} />

        {/* ── Component models in fixed orbit ── */}
        {REGISTRY.map(def => {
          const comp = (activeData as any)[def.id];
          if (!comp) return null;
          return (
            <ComponentModel
              key={`model-${def.id}`}
              def={def}
              comp={comp}
              color={colors[def.id]}
              hovered={hoveredComponent === def.name}
              selected={selectedComponent === def.name}
              onHover={onHover}
              onClick={onComponentClick}
            />
          );
        })}

        {/* ── Connection lines: component → hotspot on car ── */}
        {REGISTRY.map(def => (
          <ConnectionBeam
            key={`beam-${def.id}`}
            from={def.modelPosition}
            to={def.hotspot}
            color={colors[def.id]}
            active
            highlight={hoveredComponent === def.name || selectedComponent === def.name}
          />
        ))}

        {/* ── Hotspots on the car body ── */}
        {REGISTRY.map(def => {
          const comp = (activeData as any)[def.id];
          if (!comp) return null;
          return (
            <Hotspot
              key={def.id}
              def={def}
              comp={comp}
              color={colors[def.id]}
              hovered={hoveredComponent === def.name}
              selected={selectedComponent === def.name}
              onHover={onHover}
              onClick={onComponentClick}
            />
          );
        })}

        {/* ── Ambient particles ── */}
        {showParticles && <BackgroundParticles />}

        {/* ── Popup — fixed overlay, top-right ── */}
        {selectedComponent && popupComp && popupColor && (
          <ComponentPopup
            name={selectedComponent}
            comp={popupComp}
            color={popupColor}
            onClose={() => onSelect(null)}
          />
        )}

        {/* ── Floor grid ── */}
        <AnimatedGrid vehicleHealth={activeData.vehicle_health} />
        <Grid
          position={[0, -0.02, 0]}
          args={[30, 30]}
          cellSize={0.6}
          cellThickness={0.3}
          cellColor="#0a1a2e"
          sectionSize={3.0}
          sectionThickness={0.6}
          sectionColor="#0d2a4a"
          fadeDistance={20}
          fadeStrength={1.5}
          infiniteGrid
        />
      </Suspense>

      {/* ── Bloom + vignette ── */}
      <GlowEffects vehicleHealth={activeData.vehicle_health} />

      {/* ── User orbit controls only ── */}
      <CameraControls disablePan />

      {/* ── HUD corner overlay ── */}
      <DigitalHUDOverlay
        twinData={activeData}
        hoveredComponent={hoveredComponent}
        selectedComponent={selectedComponent}
      />
    </>
  );
});

export default function DigitalTwinScene({
  twinData,
  timelineTwinData,
  showLabels = true,
  showParticles = true,
  cameraMode: externalMode,
  onCameraModeChange,
}: Props) {
  const activeData = timelineTwinData ?? twinData;

  const {
    cameraMode,
    setCameraMode,
    hoveredComponent,
    setHoveredComponent,
    selectedComponent,
    setSelectedComponent,
    pulseTime,
    colors,
  } = useTwinAnimation(activeData);

  const activeMode = externalMode ?? cameraMode;

  function handleComponentClick(name: string) {
    const def  = REGISTRY.find(c => c.name === name);
    const mode = def?.cameraMode ?? "overview";
    setCameraMode(mode);
    onCameraModeChange?.(mode);
    setSelectedComponent(prev => prev === name ? null : name);
  }

  return (
    <Canvas
      camera={{ position: [0, 4.5, 9], fov: 58 }}
      style={{ background: BACKGROUND, width: "100%", height: "100%" }}
      gl={{ antialias: true, powerPreference: "high-performance" }}
      frameloop="always"
    >
      <fog attach="fog" args={["#060d1a", 16, 36]} />

      {activeData && colors ? (
        <InnerScene
          activeData={activeData}
          cameraMode={activeMode}
          hoveredComponent={hoveredComponent}
          selectedComponent={selectedComponent}
          pulseTime={pulseTime}
          colors={colors}
          showParticles={showParticles}
          onHover={setHoveredComponent}
          onSelect={setSelectedComponent}
          onComponentClick={handleComponentClick}
          criticalCount={activeData.critical_components.length}
        />
      ) : (
        <>
          <SceneLights />
          <CameraController mode={activeMode} />
          <Suspense fallback={null}>
            <Vehicle isOverview={false} />
            <AnimatedGrid />
          </Suspense>
          <CameraControls disablePan />
        </>
      )}
    </Canvas>
  );
}

export type { CameraMode };

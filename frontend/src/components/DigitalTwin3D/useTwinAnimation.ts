import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import * as THREE from "three";
import { healthColor } from "./WireframeMaterial";

export type CameraMode =
  | "overview"
  | "top"
  | "battery"
  | "motor"
  | "cooling"
  | "brakes"
  | "failure"
  | "auto";

export interface ComponentState {
  health: number;
  failure_probability: number;
  rul: number;
  confidence: number;
  status: string;
  sensors?: Record<string, number | string>;
}

export interface TwinData {
  vehicle_health: number;
  vehicle_status: string;
  critical_components: string[];
  battery:      ComponentState;
  motor:        ComponentState;
  cooling:      ComponentState;
  brakes:       ComponentState;
  electrical:   ComponentState;
  transmission: ComponentState;
}

// Camera positions for each mode
export const CAMERA_POSITIONS: Record<CameraMode, [number, number, number]> = {
  overview: [0,    4.5,  9.0 ],
  top:      [0,    10,   0.1 ],
  battery:  [ 4.5, 2.2,  3.5 ],
  motor:    [ 0,   2.2, -6.5 ],
  cooling:  [-4.5, 2.2, -3.5 ],
  brakes:   [ 4.5, 2.2,  3.5 ],
  failure:  [ 3.5, 3.0,  6.0 ],
  auto:     [ 0,   4.5,  9.0 ],
};

export const CAMERA_TARGETS: Record<CameraMode, [number, number, number]> = {
  overview: [0,    0.8,  0   ],
  top:      [0,    0,    0   ],
  battery:  [0,    0.5,  0.8 ],
  motor:    [0,    0.5, -1.6 ],
  cooling:  [0,    0.5, -2.1 ],
  brakes:   [-1.3, 0.2,  1.4 ],
  failure:  [0,    0.5,  0   ],
  auto:     [0,    0.8,  0   ],
};

export function useTwinAnimation(twinData: TwinData | null) {
  const [cameraMode, setCameraMode] = useState<CameraMode>("overview");
  const [hoveredComponent, setHoveredComponent]   = useState<string | null>(null);
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);
  const [pulseTime, setPulseTime] = useState(0);
  const rafRef   = useRef<number>(0);
  const startRef = useRef(performance.now());

  // Auto-camera rotation
  useEffect(() => {
    if (cameraMode !== "auto") return;
    const modes: CameraMode[] = ["overview", "battery", "motor", "cooling", "top"];
    let idx = 0;
    const interval = setInterval(() => {
      idx = (idx + 1) % modes.length;
      setCameraMode(modes[idx]);
    }, 4000);
    return () => clearInterval(interval);
  }, [cameraMode]);

  // Pulse animation clock — stable RAF loop with cleanup
  useEffect(() => {
    const tick = () => {
      setPulseTime((performance.now() - startRef.current) / 1000);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  // Derive per-component colors from health — memoized to avoid new Color objects every frame
  const colors = useMemo(() => {
    if (!twinData) return null;
    return {
      battery:      healthColor(twinData.battery.health),
      motor:        healthColor(twinData.motor.health),
      cooling:      healthColor(twinData.cooling.health),
      brakes:       healthColor(twinData.brakes.health),
      electrical:   healthColor(twinData.electrical.health),
      transmission: healthColor(twinData.transmission.health),
      body:         new THREE.Color("#38bdf8"),
    };
  }, [
    twinData?.battery.health,
    twinData?.motor.health,
    twinData?.cooling.health,
    twinData?.brakes.health,
    twinData?.electrical.health,
    twinData?.transmission.health,
  ]);

  // Stable callback — avoids re-creating on every render
  const pulseIntensity = useCallback((component: string): number => {
    if (!twinData) return 0.4;
    const comp = twinData[component as keyof TwinData] as ComponentState | undefined;
    if (!comp) return 0.4;
    const speed = comp.health < 35 ? 4 : comp.health < 60 ? 2 : 1;
    return 0.3 + Math.sin(pulseTime * speed) * 0.25;
  }, [twinData, pulseTime]);

  return {
    cameraMode,
    setCameraMode,
    hoveredComponent,
    setHoveredComponent,
    selectedComponent,
    setSelectedComponent,
    pulseTime,
    colors,
    pulseIntensity,
  };
}

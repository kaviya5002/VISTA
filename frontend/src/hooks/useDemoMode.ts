/**
 * useDemoMode — Cinematic Demo Mode
 * ─────────────────────────────────────────────────────────────────────────────
 * When active:
 *   • Camera automatically moves through every component
 *   • Timeline automatically progresses from Day 0 to Day 30
 *   • Vehicle health gradually decreases
 *   • Failure probability increases
 *   • Battery voltage decreases
 *   • Temperature increases
 *   • RUL decreases
 *   • HUD updates automatically
 *   • Labels animate automatically (driven by data changes)
 *   • Camera returns to overview
 *   • Demo loops smoothly
 *
 * Architecture: drives existing setDay + setCameraMode callbacks.
 * No new state — reuses shared timeline state and camera controller.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import type { CameraMode } from "../components/DigitalTwin3D";

// Camera tour: each entry is [mode, dwell-ms]
// Visits every component then returns to overview — loops
const TOUR: Array<[CameraMode, number]> = [
  ["overview",     2800],
  ["battery",      3200],
  ["motor",        3200],
  ["cooling",      3000],
  ["brakes",       2800],
  ["top",          2600],
  ["failure",      3000],
  ["overview",     2400],
];

// Total tour duration in ms
const TOUR_TOTAL_MS = TOUR.reduce((s, [, d]) => s + d, 0);

export interface DemoState {
  active:          boolean;
  startDemo:       () => void;
  stopDemo:        () => void;
  /** Current camera mode driven by demo (null when inactive) */
  demoCameraMode:  CameraMode | null;
  /** Current day driven by demo (null when inactive) */
  demoDay:         number | null;
  /** Progress 0–100 within current loop */
  progress:        number;
  /** Human-readable phase label */
  phaseLabel:      string;
}

function getDemoPhaseLabel(day: number, mode: CameraMode): string {
  if (day === 0)  return "🟢 All Systems Nominal — Live View";
  if (day <= 5)   return "🟡 Early Degradation Detected";
  if (day <= 10)  return "🟠 Battery Voltage Dropping";
  if (day <= 15)  return "🔴 Motor Thermal Stress — Cascade Begins";
  if (day <= 20)  return "⚠ Cooling Failure — Chain Propagating";
  if (day <= 25)  return "🚨 Multi-System Failure Imminent";
  return "🔧 AI Recommends: Immediate Service";
}

export function useDemoMode(
  setDay:        (d: number) => void,
  setCameraMode: (m: CameraMode) => void,
): DemoState {
  const [active,         setActive]         = useState(false);
  const [demoCameraMode, setDemoCameraMode] = useState<CameraMode | null>(null);
  const [demoDay,        setDemoDay]        = useState<number | null>(null);
  const [progress,       setProgress]       = useState(0);
  const [phaseLabel,     setPhaseLabel]     = useState("");

  const rafRef       = useRef<number>(0);
  const startTimeRef = useRef<number>(0);

  const tick = useCallback((now: number) => {
    const elapsed = now - startTimeRef.current;
    // Position within the current loop (0 → TOUR_TOTAL_MS), loops continuously
    const loopMs  = elapsed % TOUR_TOTAL_MS;

    // Determine which camera stop we're at
    let acc = 0;
    let mode: CameraMode = "overview";
    for (const [m, dwell] of TOUR) {
      acc += dwell;
      if (loopMs < acc) { mode = m; break; }
    }

    // Day: 0 → 30 over one full loop, then resets to 0 and loops
    const day = Math.round((loopMs / TOUR_TOTAL_MS) * 30);

    // Progress within loop (0–100)
    const prog = (loopMs / TOUR_TOTAL_MS) * 100;

    setDemoCameraMode(mode);
    setDemoDay(day);
    setProgress(prog);
    setPhaseLabel(getDemoPhaseLabel(day, mode));

    // Drive external state
    setCameraMode(mode);
    setDay(day);

    rafRef.current = requestAnimationFrame(tick);
  }, [setDay, setCameraMode]);

  useEffect(() => {
    if (!active) return;
    startTimeRef.current = performance.now();
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [active, tick]);

  const startDemo = useCallback(() => {
    setActive(true);
    setProgress(0);
  }, []);

  const stopDemo = useCallback(() => {
    setActive(false);
    cancelAnimationFrame(rafRef.current);
    setDemoCameraMode(null);
    setDemoDay(null);
    setProgress(0);
    setPhaseLabel("");
    // Return to live view
    setDay(0);
    setCameraMode("overview");
  }, [setDay, setCameraMode]);

  return {
    active,
    startDemo,
    stopDemo,
    demoCameraMode,
    demoDay,
    progress,
    phaseLabel,
  };
}

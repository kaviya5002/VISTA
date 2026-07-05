/**
 * DemoMode — Phase 8
 *
 * Automated 90-second demo sequence.
 * Drives: health degradation → battery warning → motor critical →
 * failure chain → AI popup → timeline advance → recommendation change.
 *
 * Returns a `demoTwinData` override and `demoDay` that replace live data
 * when demo is active. The parent just swaps its data source.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import type { TwinData } from "../components/DigitalTwin3D";

export interface DemoState {
  active:       boolean;
  demoTwinData: TwinData | null;
  demoDay:      number;
  phase:        number;   // 0-7
  phaseLabel:   string;
  progress:     number;   // 0-100
  start:        () => void;
  stop:         () => void;
}

// ── Demo script: 8 phases × ~11 seconds each = ~90 seconds ──────────────────

interface DemoPhase {
  label:    string;
  duration: number;   // ms
  day:      number;
  twin:     Partial<TwinData>;
}

function makeComp(health: number, fp: number, rul: number) {
  return {
    health,
    failure_probability: fp,
    rul,
    confidence: 92,
    status: health >= 75 ? "Healthy" : health >= 45 ? "Warning" : "Critical",
    sensors: {},
  };
}

const DEMO_PHASES: DemoPhase[] = [
  {
    label: "🟢 All Systems Nominal",
    duration: 8000,
    day: 0,
    twin: {
      vehicle_health: 91, vehicle_status: "Healthy", critical_components: [],
      battery: makeComp(92, 0.05, 280), motor: makeComp(89, 0.08, 260),
      cooling: makeComp(94, 0.04, 300), brakes: makeComp(88, 0.06, 240),
      electrical: makeComp(91, 0.05, 270), transmission: makeComp(90, 0.06, 265),
    },
  },
  {
    label: "🟡 Battery Voltage Dropping",
    duration: 10000,
    day: 5,
    twin: {
      vehicle_health: 78, vehicle_status: "Warning", critical_components: [],
      battery: makeComp(68, 0.28, 45), motor: makeComp(85, 0.12, 240),
      cooling: makeComp(91, 0.06, 290), brakes: makeComp(86, 0.08, 230),
      electrical: makeComp(88, 0.09, 260), transmission: makeComp(87, 0.08, 255),
    },
  },
  {
    label: "🟠 Battery Critical — Thermal Stress",
    duration: 12000,
    day: 10,
    twin: {
      vehicle_health: 61, vehicle_status: "Warning", critical_components: ["Battery"],
      battery: makeComp(38, 0.72, 18), motor: makeComp(79, 0.22, 200),
      cooling: makeComp(85, 0.14, 240), brakes: makeComp(82, 0.12, 210),
      electrical: makeComp(81, 0.16, 230), transmission: makeComp(83, 0.11, 240),
    },
  },
  {
    label: "🔴 Motor Overheating — Cascade Begins",
    duration: 12000,
    day: 15,
    twin: {
      vehicle_health: 44, vehicle_status: "Critical", critical_components: ["Battery", "Motor"],
      battery: makeComp(28, 0.85, 8), motor: makeComp(41, 0.68, 22),
      cooling: makeComp(72, 0.32, 160), brakes: makeComp(78, 0.18, 190),
      electrical: makeComp(70, 0.28, 180), transmission: makeComp(76, 0.20, 200),
    },
  },
  {
    label: "⚠ Cooling Failure — Chain Propagating",
    duration: 12000,
    day: 20,
    twin: {
      vehicle_health: 31, vehicle_status: "Critical", critical_components: ["Battery", "Motor", "Cooling"],
      battery: makeComp(18, 0.94, 3), motor: makeComp(29, 0.88, 9),
      cooling: makeComp(32, 0.82, 12), brakes: makeComp(71, 0.28, 160),
      electrical: makeComp(58, 0.44, 120), transmission: makeComp(65, 0.32, 150),
    },
  },
  {
    label: "🚨 Multi-System Failure Imminent",
    duration: 12000,
    day: 25,
    twin: {
      vehicle_health: 19, vehicle_status: "Critical",
      critical_components: ["Battery", "Motor", "Cooling", "Electrical"],
      battery: makeComp(11, 0.97, 1), motor: makeComp(18, 0.94, 3),
      cooling: makeComp(21, 0.91, 4), brakes: makeComp(62, 0.38, 130),
      electrical: makeComp(34, 0.76, 14), transmission: makeComp(52, 0.48, 90),
    },
  },
  {
    label: "🔧 AI Recommends: Immediate Service",
    duration: 12000,
    day: 28,
    twin: {
      vehicle_health: 12, vehicle_status: "Critical",
      critical_components: ["Battery", "Motor", "Cooling", "Electrical", "Transmission"],
      battery: makeComp(8, 0.99, 0), motor: makeComp(12, 0.97, 1),
      cooling: makeComp(14, 0.95, 2), brakes: makeComp(55, 0.48, 100),
      electrical: makeComp(22, 0.88, 5), transmission: makeComp(38, 0.72, 18),
    },
  },
  {
    label: "✅ After Repair — Systems Restored",
    duration: 10000,
    day: 0,
    twin: {
      vehicle_health: 95, vehicle_status: "Healthy", critical_components: [],
      battery: makeComp(96, 0.03, 320), motor: makeComp(94, 0.04, 310),
      cooling: makeComp(97, 0.02, 330), brakes: makeComp(93, 0.04, 300),
      electrical: makeComp(95, 0.03, 315), transmission: makeComp(94, 0.04, 305),
    },
  },
];

const TOTAL_DURATION = DEMO_PHASES.reduce((s, p) => s + p.duration, 0);

export function useDemoMode(): DemoState {
  const [active,  setActive]  = useState(false);
  const [phase,   setPhase]   = useState(0);
  const [progress, setProgress] = useState(0);
  const timerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rafRef    = useRef<number>(0);
  const startTime = useRef(0);
  const phaseStart = useRef(0);

  const stop = useCallback(() => {
    setActive(false);
    setPhase(0);
    setProgress(0);
    if (timerRef.current) clearTimeout(timerRef.current);
    cancelAnimationFrame(rafRef.current);
  }, []);

  const runPhase = useCallback((idx: number) => {
    if (idx >= DEMO_PHASES.length) { stop(); return; }
    setPhase(idx);
    phaseStart.current = performance.now();

    timerRef.current = setTimeout(() => runPhase(idx + 1), DEMO_PHASES[idx].duration);
  }, [stop]);

  const start = useCallback(() => {
    setActive(true);
    setPhase(0);
    startTime.current = performance.now();
    phaseStart.current = performance.now();
    runPhase(0);

    // Progress animation
    const tick = () => {
      const elapsed = performance.now() - startTime.current;
      setProgress(Math.min(100, (elapsed / TOTAL_DURATION) * 100));
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [runPhase]);

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    cancelAnimationFrame(rafRef.current);
  }, []);

  const currentPhase = DEMO_PHASES[phase];

  return {
    active,
    demoTwinData: active ? (currentPhase.twin as TwinData) : null,
    demoDay:      active ? currentPhase.day : 0,
    phase,
    phaseLabel:   currentPhase.label,
    progress,
    start,
    stop,
  };
}

// ── Demo control bar ──────────────────────────────────────────────────────────

interface BarProps {
  demo: DemoState;
}

export function DemoBar({ demo }: BarProps) {
  return (
    <div style={{
      position: "fixed", bottom: 20, left: "50%", transform: "translateX(-50%)",
      zIndex: 900,
      background: "rgba(5,7,12,0.97)",
      border: `1px solid ${demo.active ? "rgba(239,68,68,0.4)" : "rgba(56,189,248,0.2)"}`,
      borderRadius: 12,
      padding: "10px 18px",
      display: "flex", alignItems: "center", gap: 14,
      boxShadow: demo.active ? "0 0 30px rgba(239,68,68,0.2)" : "0 4px 20px rgba(0,0,0,0.4)",
      fontFamily: "system-ui, sans-serif",
      minWidth: 360,
    }}>
      {demo.active ? (
        <>
          {/* Progress bar */}
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ fontSize: 10, color: "#ef4444", fontWeight: 700 }}>
                🎬 DEMO MODE
              </span>
              <span style={{ fontSize: 10, color: "#64748b" }}>
                Phase {demo.phase + 1}/{DEMO_PHASES.length}
              </span>
            </div>
            <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: 2, height: 3, marginBottom: 5 }}>
              <div style={{
                width: `${demo.progress}%`, height: "100%", borderRadius: 2,
                background: "linear-gradient(90deg, #38bdf8, #ef4444)",
                transition: "width 0.1s",
              }} />
            </div>
            <div style={{ fontSize: 11, color: "#94a3b8" }}>{demo.phaseLabel}</div>
          </div>
          <button onClick={demo.stop} style={{
            padding: "6px 14px", borderRadius: 8, cursor: "pointer",
            background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
            color: "#ef4444", fontSize: 11, fontWeight: 700, whiteSpace: "nowrap",
          }}>Stop Demo</button>
        </>
      ) : (
        <>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>🎬 Demo Mode</div>
            <div style={{ fontSize: 10, color: "#475569" }}>90-second automated failure sequence</div>
          </div>
          <button onClick={demo.start} style={{
            padding: "8px 18px", borderRadius: 8, cursor: "pointer",
            background: "linear-gradient(135deg, rgba(56,189,248,0.2), rgba(129,140,248,0.15))",
            border: "1px solid rgba(56,189,248,0.35)",
            color: "#38bdf8", fontSize: 12, fontWeight: 700, whiteSpace: "nowrap",
          }}>▶ Start Demo</button>
        </>
      )}
    </div>
  );
}

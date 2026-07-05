/**
 * ComponentPopup — fixed overlay panel (not 3D world-space).
 * Renders as an HTML div anchored to the top-right of the canvas.
 * Preserves all existing data: health, sensors, AI recommendation, RUL.
 */
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { REGISTRY_MAP } from "./ComponentRegistry";
import type { ComponentState } from "./useTwinAnimation";

function recommendation(comp: ComponentState): string {
  if (comp.health < 25) return "⚠️ Replace immediately";
  if (comp.health < 50) return "🔧 Schedule within 7 days";
  if (comp.health < 75) return "📋 Monitor closely";
  return "✅ Operating normally";
}

function rulLabel(rul: number): string {
  if (rul >= 365) return `${Math.round(rul / 30)}mo`;
  if (rul >= 30)  return `${Math.round(rul / 7)}wk`;
  return `${rul}d`;
}

function formatSensor(key: string, val: number | string): string {
  const n = Number(val);
  if (isNaN(n)) return String(val);
  const units: Record<string, string> = {
    voltage: "V", temperature: "°C", rpm: "rpm",
    charge_level: "%", efficiency: "%", pressure: "bar",
    flow_rate: "L/min", speed: "km/h",
  };
  const unit = units[key] ?? "";
  const decimals = ["rpm", "charge_level", "efficiency"].includes(key) ? 0 : 1;
  return `${n.toFixed(decimals)}${unit}`;
}

function sensorLabel(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

interface Props {
  name:    string;
  comp:    ComponentState;
  color:   THREE.Color;
  onClose: () => void;
}

export default function ComponentPopup({ name, comp, color, onClose }: Props) {
  const def = REGISTRY_MAP[name.toLowerCase()];
  const hex = "#" + color.getHexString();
  const hc  = comp.health >= 75 ? "#22c55e" : comp.health >= 45 ? "#f59e0b" : "#ef4444";
  const fp  = Math.round(comp.failure_probability * 100);

  const sensorEntries = Object.entries(comp.sensors ?? {}).filter(
    ([, v]) => v !== null && v !== undefined && v !== ""
  );

  // Anchor at a fixed screen-space position — top-right, always visible
  return (
    <Html
      position={[0, 0, 0]}
      style={{ position: "absolute", top: 16, right: 16, pointerEvents: "none" }}
      zIndexRange={[30, 0]}
      prepend
    >
      <div style={{
        width: 220,
        background: "rgba(3,5,12,0.97)",
        border: `1px solid ${hex}60`,
        borderRadius: 10,
        padding: "14px 16px",
        color: "#e2e8f0",
        fontFamily: "monospace",
        boxShadow: `0 0 24px ${hex}28, 0 4px 20px rgba(0,0,0,0.8)`,
        pointerEvents: "auto",
        userSelect: "none",
      }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 800, color: hex }}>
            {def?.icon ?? "🔩"} {name}
          </span>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: 17, lineHeight: 1, padding: 0 }}
          >×</button>
        </div>

        {/* AI Metrics */}
        {[
          { label: "Health",         value: `${comp.health}%`,                 vc: hc },
          { label: "Failure Risk",   value: `${fp}%`,                          vc: fp > 60 ? "#ef4444" : fp > 35 ? "#f59e0b" : "#22c55e" },
          { label: "Remaining Life", value: rulLabel(comp.rul),                vc: "#94a3b8" },
          { label: "Confidence",     value: `${Math.round(comp.confidence)}%`, vc: "#38bdf8" },
        ].map(({ label, value, vc }) => (
          <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <span style={{ fontSize: 10, color: "#64748b" }}>{label}</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: vc }}>{value}</span>
          </div>
        ))}

        {/* Health bar */}
        <div style={{ margin: "8px 0 7px", background: "#1e293b", borderRadius: 3, height: 4 }}>
          <div style={{
            width: `${comp.health}%`, height: "100%", borderRadius: 3,
            background: `linear-gradient(90deg,${hc}88,${hc})`,
            transition: "width 0.6s",
          }} />
        </div>

        {/* Live Sensors */}
        {sensorEntries.length > 0 && (
          <>
            <div style={{ fontSize: 8, color: "#334155", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4, marginTop: 3 }}>
              Live Sensors
            </div>
            {sensorEntries.map(([key, val]) => (
              <div key={key} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
                <span style={{ fontSize: 9, color: "#475569" }}>{sensorLabel(key)}</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: "#38bdf8", fontFamily: "monospace" }}>
                  {formatSensor(key, val as number | string)}
                </span>
              </div>
            ))}
          </>
        )}

        {/* AI Recommendation */}
        <div style={{ marginTop: 8, padding: "6px 9px", borderRadius: 6, background: `${hex}0c`, border: `1px solid ${hex}20`, fontSize: 10, color: "#cbd5e1", lineHeight: 1.5 }}>
          {recommendation(comp)}
        </div>

        <div style={{ marginTop: 6, textAlign: "center" }}>
          <span style={{ fontSize: 9, padding: "2px 7px", borderRadius: 8, background: hc + "18", border: `1px solid ${hc}44`, color: hc }}>
            {comp.status}
          </span>
        </div>
      </div>
    </Html>
  );
}

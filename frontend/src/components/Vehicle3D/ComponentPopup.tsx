/**
 * ComponentPopup
 *
 * Slides in from the right when the user clicks a vehicle part.
 * Shows: health bar, sensors, AI explanation, repair button.
 */

import { useState } from "react";
import api from "../../services/api";
import { healthToColor, COMPONENT_LABELS } from "./utils";
import type { ComponentKey } from "./utils";

interface Props {
  componentKey: ComponentKey;
  twin:         Record<string, any>;       // full component twin payload
  vehicleId:    number;
  onRepaired:   (newTwin: Record<string, any>) => void;
  onClose:      () => void;
}

function HealthBar({ value, color }: { value: number; color: string }) {
  return (
    <div style={{ background: "#1e293b", borderRadius: 6, height: 8, overflow: "hidden", marginTop: 4 }}>
      <div style={{ width: `${value}%`, background: color, height: "100%", transition: "width 0.5s" }} />
    </div>
  );
}

function Row({ label, value, unit = "" }: { label: string; value: any; unit?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "4px 0", borderBottom: "1px solid #1e293b" }}>
      <span style={{ color: "#64748b" }}>{label}</span>
      <span style={{ color: "#f1f5f9", fontWeight: 600 }}>{value ?? "—"}{unit}</span>
    </div>
  );
}

export default function ComponentPopup({ componentKey, twin, vehicleId, onRepaired, onClose }: Props) {
  const [repairing, setRepairing] = useState(false);
  const [repaired,  setRepaired]  = useState(false);

  const data    = twin[componentKey];
  const explain = twin.explanations?.find((e: any) => e.component === data?.component);
  const color   = healthToColor(data?.health ?? 50);
  const label   = COMPONENT_LABELS[componentKey];

  if (!data) return null;

  async function handleRepair() {
    setRepairing(true);
    try {
      const res = await api.post(`/digital_twin/component/${vehicleId}/repair`, {
        components: [componentKey],
      });
      onRepaired(res.data);
      setRepaired(true);
    } finally {
      setRepairing(false);
    }
  }

  return (
    <div style={{
      position: "absolute", top: 0, right: 0,
      width: 300, height: "100%",
      background: "#0f172a",
      border: "1px solid #1e293b",
      borderRadius: "0 14px 14px 0",
      padding: 20,
      overflowY: "auto",
      display: "flex",
      flexDirection: "column",
      gap: 14,
      zIndex: 10,
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontWeight: 700, fontSize: 16, color: "#f1f5f9" }}>{label}</span>
        <button
          onClick={onClose}
          style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 18 }}
        >✕</button>
      </div>

      {/* Health */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ color: "#94a3b8", fontSize: 13 }}>Health</span>
          <span style={{ color, fontWeight: 700, fontSize: 22 }}>{data.health}%</span>
        </div>
        <HealthBar value={data.health} color={color} />
      </div>

      {/* Status badge */}
      <div style={{
        background: color + "18", border: `1px solid ${color}`,
        borderRadius: 8, padding: "6px 12px", fontSize: 13,
        color, fontWeight: 600, textAlign: "center",
      }}>
        {data.risk_color} {data.status} — {data.risk} Risk
      </div>

      {/* Key metrics */}
      <div>
        <Row label="Failure Probability" value={data.failure_probability} unit="%" />
        <Row label="RUL"                 value={data.rul}                  unit=" days" />
        <Row label="Confidence"          value={data.confidence}            unit="%" />
      </div>

      {/* Sensors */}
      {data.sensors && (
        <div>
          <div style={{ color: "#475569", fontSize: 12, marginBottom: 4 }}>SENSORS</div>
          {Object.entries(data.sensors).map(([k, v]) => (
            <Row key={k} label={k.replace(/_/g, " ")} value={String(v)} />
          ))}
        </div>
      )}

      {/* AI Explanation */}
      {explain && (
        <div>
          <div style={{ color: "#475569", fontSize: 12, marginBottom: 6 }}>
            🧠 AI EXPLANATION · {explain.confidence}% confidence
          </div>
          <ul style={{ margin: 0, paddingLeft: 16, display: "flex", flexDirection: "column", gap: 4 }}>
            {explain.reasons.map((r: string, i: number) => (
              <li key={i} style={{ fontSize: 13, color: "#94a3b8" }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Trend */}
      {data.trend && (
        <div style={{ fontSize: 13, color: "#64748b" }}>
          Trend:{" "}
          <span style={{
            color: data.trend.direction === "Improving" ? "#22c55e"
                 : data.trend.direction === "Degrading"  ? "#ef4444" : "#9ca3af",
            fontWeight: 600,
          }}>
            {data.trend.direction}
          </span>
          {" "}(slope {data.trend.slope > 0 ? "+" : ""}{data.trend.slope})
        </div>
      )}

      {/* Repair button */}
      <button
        onClick={handleRepair}
        disabled={repairing || repaired}
        style={{
          marginTop: "auto",
          padding: "10px 0",
          background: repaired ? "#15803d" : "#7c3aed",
          color: "white",
          border: "none",
          borderRadius: 8,
          fontWeight: 700,
          fontSize: 14,
          cursor: repairing || repaired ? "default" : "pointer",
          opacity: repairing ? 0.7 : 1,
          transition: "background 0.3s",
        }}
      >
        {repaired ? "✅ Repaired" : repairing ? "Simulating…" : `🔧 Simulate Repair`}
      </button>
    </div>
  );
}

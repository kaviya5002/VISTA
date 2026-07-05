import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { healthColor, statusColor } from "../hooks/useCounter";

interface Vehicle { vehicle_id: number; health_score: number; status: string;
  failure_probability: number; remaining_useful_life_days: number;
  battery_voltage: number; temperature: number; }

interface Tooltip { v: Vehicle; x: number; y: number; }

export default function FleetHeatmap({ vehicles }: { vehicles: Vehicle[] }) {
  const [tip, setTip] = useState<Tooltip | null>(null);
  const navigate = useNavigate();

  return (
    <div style={{ position: "relative" }}>
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(10, 1fr)",
        gap: 6,
      }}>
        {vehicles.map(v => {
          const color = statusColor(v.status);
          return (
            <div
              key={v.vehicle_id}
              onClick={() => navigate(`/vehicle/${v.vehicle_id}`)}
              onMouseEnter={e => {
                const r = (e.target as HTMLElement).getBoundingClientRect();
                setTip({ v, x: r.left, y: r.top });
              }}
              onMouseLeave={() => setTip(null)}
              style={{
                width: "100%", aspectRatio: "1",
                borderRadius: 6,
                background: color + "22",
                border: `1px solid ${color}55`,
                cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 9, fontWeight: 700, color,
                transition: "all 0.15s",
                boxShadow: tip?.v.vehicle_id === v.vehicle_id ? `0 0 10px ${color}` : "none",
              }}
            >
              {v.vehicle_id}
            </div>
          );
        })}
      </div>

      {/* Tooltip */}
      {tip && (
        <div style={{
          position: "fixed",
          left: Math.min(tip.x + 16, window.innerWidth - 220),
          top: tip.y - 140,
          zIndex: 200,
          background: "rgba(5,7,10,0.95)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 12,
          padding: "12px 16px",
          width: 200,
          pointerEvents: "none",
          backdropFilter: "blur(20px)",
        }}>
          <div style={{ fontWeight: 700, marginBottom: 8, color: statusColor(tip.v.status) }}>
            Vehicle {tip.v.vehicle_id} · {tip.v.status}
          </div>
          {[
            ["Health",    `${tip.v.health_score}%`,              healthColor(tip.v.health_score)],
            ["Failure",   `${tip.v.failure_probability}%`,       tip.v.failure_probability > 60 ? "#F87171" : "#FBBF24"],
            ["RUL",       `${tip.v.remaining_useful_life_days}d`, "#38BDF8"],
            ["Voltage",   `${tip.v.battery_voltage}V`,           "#A78BFA"],
            ["Temp",      `${tip.v.temperature}°C`,              tip.v.temperature > 90 ? "#F87171" : "#34D399"],
          ].map(([label, val, col]) => (
            <div key={label as string} style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
              <span style={{ color: "#64748B" }}>{label}</span>
              <span style={{ color: col as string, fontWeight: 600 }}>{val}</span>
            </div>
          ))}
          <div style={{ marginTop: 8, fontSize: 11, color: "#38BDF8" }}>Click to open twin →</div>
        </div>
      )}
    </div>
  );
}

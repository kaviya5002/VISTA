/**
 * InteractiveTwin
 *
 * Top-level 3D Digital Twin experience:
 *   - VehicleScene  (Three.js canvas)
 *   - ForecastSlider (morphs vehicle colors into future)
 *   - ComponentPopup (click-to-inspect panel)
 *
 * Usage: <InteractiveTwin vehicleId={44} />
 */

import { useEffect, useState } from "react";
import api from "../../services/api";
import VehicleScene    from "./VehicleScene";
import ForecastSlider  from "./ForecastSlider";
import ComponentPopup  from "./ComponentPopup";
import type { ComponentKey } from "./utils";

interface Props { vehicleId: number; }

export default function InteractiveTwin({ vehicleId }: Props) {
  const [twin,         setTwin]         = useState<Record<string, any> | null>(null);
  const [forecastTwin, setForecastTwin] = useState<Record<string, any> | null>(null);
  const [selected,     setSelected]     = useState<ComponentKey | null>(null);

  useEffect(() => {
    api.get(`/digital_twin/component/${vehicleId}`)
      .then(r => setTwin(r.data))
      .catch(console.error);
  }, [vehicleId]);

  function handleRepaired(newTwin: Record<string, any>) {
    setTwin(newTwin);
    setForecastTwin(null);   // reset forecast after repair
  }

  const vh     = twin?.vehicle_health ?? 0;
  const status = twin?.vehicle_status ?? "…";
  const statusColor = status === "Healthy" ? "#22c55e" : status === "Warning" ? "#f97316" : "#ef4444";

  return (
    <div style={{
      background: "#0a0f1e",
      border: "1px solid #1e293b",
      borderRadius: 16,
      padding: 0,
      overflow: "hidden",
    }}>
      {/* Title bar */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "14px 20px",
        borderBottom: "1px solid #1e293b",
      }}>
        <span style={{ fontWeight: 700, fontSize: 16, color: "#f1f5f9" }}>
          🚗 Interactive Digital Twin · Vehicle {vehicleId}
        </span>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span style={{ color: statusColor, fontWeight: 700, fontSize: 14 }}>{status}</span>
          <span style={{
            background: "#1e293b", borderRadius: 8, padding: "3px 12px",
            color: statusColor, fontWeight: 700, fontSize: 14,
          }}>
            {vh}% health
          </span>
        </div>
      </div>

      {/* Main body: scene + optional popup side-by-side */}
      <div style={{ position: "relative", display: "flex" }}>

        {/* 3D Scene — full width, shrinks when popup is open */}
        <div style={{ flex: 1, transition: "flex 0.3s" }}>
          <VehicleScene
            twin={twin}
            forecastTwin={forecastTwin}
            selected={selected}
            onSelect={k => setSelected(k === selected ? null : k)}
          />
        </div>

        {/* Popup panel */}
        {selected && twin && (
          <div style={{ width: 300, position: "relative", borderLeft: "1px solid #1e293b" }}>
            <ComponentPopup
              componentKey={selected}
              twin={twin}
              vehicleId={vehicleId}
              onRepaired={handleRepaired}
              onClose={() => setSelected(null)}
            />
          </div>
        )}
      </div>

      {/* Forecast slider */}
      <div style={{ padding: "0 20px 20px" }}>
        <ForecastSlider
          vehicleId={vehicleId}
          baseTwin={twin}
          onForecast={setForecastTwin}
        />
      </div>

      {/* Component score chips */}
      {twin && (
        <div style={{
          display: "flex", flexWrap: "wrap", gap: 8,
          padding: "0 20px 20px",
        }}>
          {(["battery","motor","cooling","brakes","electrical","transmission"] as ComponentKey[]).map(k => {
            const h = twin[k]?.health ?? 0;
            const rc = twin[k]?.risk_color ?? "⬤";
            return (
              <button
                key={k}
                onClick={() => setSelected(k === selected ? null : k)}
                style={{
                  background: selected === k ? "#1e293b" : "#0f172a",
                  border: `1px solid ${selected === k ? "#7c3aed" : "#1e293b"}`,
                  borderRadius: 8, padding: "6px 14px",
                  color: "#f1f5f9", fontSize: 13, cursor: "pointer",
                  display: "flex", gap: 6, alignItems: "center",
                }}
              >
                {rc} <span style={{ textTransform: "capitalize" }}>{k}</span>
                <span style={{ fontWeight: 700 }}>{h}%</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

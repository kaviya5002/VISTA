/**
 * ForecastSlider
 *
 * Moves between Today / Day 7 / Day 15 / Day 30 forecast snapshots.
 * Calls /component_twin/:id/forecast and morphs the 3D vehicle colours.
 */

import { useEffect, useState } from "react";
import api from "../../services/api";

interface Props {
  vehicleId:   number;
  baseTwin:    Record<string, any> | null;
  onForecast:  (twin: Record<string, any> | null) => void;
}

const DAYS = [0, 7, 15, 30];

// Flatten forecast shape { day7: {...}, day15: {...}, day30: {...} }
// into component-twin-like shape so VehicleModel can read .health
function buildForecastTwin(base: Record<string, any>, forecast: Record<string, any>, day: number): Record<string, any> {
  if (day === 0) return base;

  const key = `day${day}` as "day7" | "day15" | "day30";
  const merged: Record<string, any> = { ...base };

  // For each component, override health/rul from the forecast
  (["battery", "motor", "cooling", "brakes", "electrical", "transmission"] as const).forEach(comp => {
    const forecastComp = forecast[comp]?.[key];
    if (forecastComp && merged[comp]) {
      merged[comp] = {
        ...merged[comp],
        health:              forecastComp.health            ?? merged[comp].health,
        failure_probability: forecastComp.failure_probability ?? merged[comp].failure_probability,
        rul:                 forecastComp.rul               ?? merged[comp].rul,
      };
    }
  });

  return merged;
}

export default function ForecastSlider({ vehicleId, baseTwin, onForecast }: Props) {
  const [day,      setDay]      = useState(0);
  const [forecast, setForecast] = useState<Record<string, any> | null>(null);
  const [loading,  setLoading]  = useState(false);

  useEffect(() => {
    if (!vehicleId) return;
    setLoading(true);
    api.get(`/component_twin/${vehicleId}/forecast`)
      .then(r => setForecast(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [vehicleId]);

  useEffect(() => {
    if (!baseTwin) return;
    if (day === 0 || !forecast) {
      onForecast(null);
    } else {
      onForecast(buildForecastTwin(baseTwin, forecast, day));
    }
  }, [day, forecast, baseTwin]);

  return (
    <div style={{
      background: "#0f172a",
      border: "1px solid #1e293b",
      borderRadius: 10,
      padding: "12px 20px",
      display: "flex",
      flexDirection: "column",
      gap: 8,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ color: "#94a3b8", fontSize: 13 }}>
          🔮 Forecast Mode{loading ? " (loading…)" : ""}
        </span>
        <span style={{
          color: day === 0 ? "#22c55e" : day <= 7 ? "#facc15" : day <= 15 ? "#f97316" : "#ef4444",
          fontWeight: 700, fontSize: 14,
        }}>
          {day === 0 ? "Today" : `+${day} Days`}
        </span>
      </div>

      <input
        type="range"
        min={0} max={3} step={1}
        value={DAYS.indexOf(day)}
        onChange={e => setDay(DAYS[Number(e.target.value)])}
        style={{ width: "100%", accentColor: "#7c3aed", cursor: "pointer" }}
      />

      {/* Day labels */}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#475569" }}>
        {DAYS.map(d => (
          <span
            key={d}
            style={{ cursor: "pointer", color: d === day ? "#a78bfa" : "#475569", fontWeight: d === day ? 700 : 400 }}
            onClick={() => setDay(d)}
          >
            {d === 0 ? "Today" : `+${d}d`}
          </span>
        ))}
      </div>
    </div>
  );
}

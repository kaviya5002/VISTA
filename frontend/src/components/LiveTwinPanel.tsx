/**
 * LiveTwinPanel
 *
 * Displays the real-time dynamic digital twin for a single vehicle.
 * Polls /twin/state + /twin/events + /twin/history every 2 s.
 * Shows: lifecycle badge, health meter, trend sparkline, sensor readings,
 *        auto-detected events feed.
 */
import { useTwinState } from "../hooks/useTwinState";
import type { TwinEvent } from "../hooks/useTwinState";

interface Props { vehicleId: number | string; }

const LC_COLOR: Record<string, string> = {
  Healthy:   "#22c55e",
  Degrading: "#facc15",
  Warning:   "#f97316",
  Critical:  "#ef4444",
  Repair:    "#a855f7",
  Recovered: "#22c55e",
};

const SEV_COLOR: Record<string, string> = {
  Info:     "#60a5fa",
  Warning:  "#f97316",
  Critical: "#ef4444",
};

function Sparkline({ series }: { series: { health: number }[] }) {
  if (series.length < 2) return null;
  const W = 200, H = 48, pad = 4;
  const vals = series.map(s => s.health);
  const min  = Math.min(...vals);
  const max  = Math.max(...vals);
  const range = max - min || 1;
  const pts = vals.map((v, i) => {
    const x = pad + (i / (vals.length - 1)) * (W - pad * 2);
    const y = H - pad - ((v - min) / range) * (H - pad * 2);
    return `${x},${y}`;
  }).join(" ");

  const last = vals[vals.length - 1];
  const color = last >= 75 ? "#22c55e" : last >= 45 ? "#f97316" : "#ef4444";

  return (
    <svg width={W} height={H} style={{ display: "block" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
      {/* Latest dot */}
      {(() => {
        const [lx, ly] = pts.split(" ").pop()!.split(",").map(Number);
        return <circle cx={lx} cy={ly} r={3} fill={color} />;
      })()}
    </svg>
  );
}

function SensorPill({ label, value, unit }: { label: string; value: any; unit?: string }) {
  return (
    <div style={{
      background: "#16213e",
      borderRadius: 8,
      padding: "8px 14px",
      fontSize: 13,
      display: "flex",
      flexDirection: "column",
      gap: 2,
      minWidth: 90,
    }}>
      <span style={{ color: "#6b7280", fontSize: 11 }}>{label}</span>
      <span style={{ color: "#f1f5f9", fontWeight: 700 }}>
        {value ?? "—"}{unit ? ` ${unit}` : ""}
      </span>
    </div>
  );
}

function EventItem({ ev }: { ev: TwinEvent }) {
  const color = SEV_COLOR[ev.severity] ?? "#9ca3af";
  const time  = new Date(ev.ts * 1000).toLocaleTimeString();
  return (
    <div style={{
      display: "flex", gap: 10, alignItems: "flex-start",
      padding: "6px 0", borderBottom: "1px solid #1e293b",
    }}>
      <span style={{ color, fontSize: 11, whiteSpace: "nowrap", paddingTop: 2 }}>{time}</span>
      <span style={{ fontSize: 13, color: "#e2e8f0" }}>{ev.message}</span>
      <span style={{
        marginLeft: "auto", fontSize: 11, color,
        border: `1px solid ${color}`, borderRadius: 4, padding: "1px 6px", whiteSpace: "nowrap",
      }}>{ev.kind}</span>
    </div>
  );
}

export default function LiveTwinPanel({ vehicleId }: Props) {
  const { state, events, history, ready } = useTwinState(vehicleId);

  if (!ready || !state) {
    return (
      <div style={{ padding: 20, color: "#6b7280", fontSize: 14 }}>
        ⏳ Waiting for live twin data… (WebSocket must be active)
      </div>
    );
  }

  const { current, summary, lifecycle } = state;
  const lcColor = LC_COLOR[lifecycle] ?? "#9ca3af";
  const dirArrow = summary.direction === "Improving" ? "▲"
                 : summary.direction === "Degrading"  ? "▼" : "●";
  const dirColor = summary.direction === "Improving" ? "#22c55e"
                 : summary.direction === "Degrading"  ? "#ef4444" : "#9ca3af";

  return (
    <div style={{
      background: "#0f172a",
      border: "1px solid #1e293b",
      borderRadius: 14,
      padding: 20,
      display: "flex",
      flexDirection: "column",
      gap: 16,
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontWeight: 700, fontSize: 16, color: "#f1f5f9" }}>
          ⚡ Live Digital Twin
        </span>
        <span style={{
          background: lcColor + "22",
          color: lcColor,
          border: `1px solid ${lcColor}`,
          borderRadius: 20,
          padding: "3px 12px",
          fontSize: 13,
          fontWeight: 600,
        }}>{lifecycle}</span>
      </div>

      {/* Health meter */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <span style={{ color: "#94a3b8", fontSize: 13 }}>Health</span>
          <span style={{ color: lcColor, fontWeight: 700, fontSize: 20 }}>
            {current.health}%
          </span>
        </div>
        <div style={{ background: "#1e293b", borderRadius: 6, height: 10, overflow: "hidden" }}>
          <div style={{
            width: `${current.health}%`,
            background: lcColor,
            height: "100%",
            transition: "width 0.6s ease",
          }} />
        </div>
      </div>

      {/* Sparkline + trend */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <Sparkline series={history} />
        <div style={{ fontSize: 13 }}>
          <div style={{ color: dirColor, fontWeight: 700 }}>
            {dirArrow} {summary.direction}
          </div>
          <div style={{ color: "#475569", fontSize: 12 }}>
            slope {summary.slope > 0 ? "+" : ""}{summary.slope}
          </div>
          <div style={{ color: "#475569", fontSize: 12 }}>
            {summary.samples} samples
          </div>
        </div>
      </div>

      {/* Sensor pills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <SensorPill label="Temperature" value={current.temperature} unit="°C" />
        <SensorPill label="Voltage"     value={current.battery_voltage} unit="V" />
        <SensorPill label="RPM"         value={current.rpm} />
        <SensorPill label="Speed"       value={current.speed} unit="km/h" />
        <SensorPill label="Failure Prob" value={current.failure_probability} unit="%" />
        <SensorPill label="RUL"         value={current.rul} unit="days" />
      </div>

      {/* Events feed */}
      {events.length > 0 && (
        <div>
          <div style={{ color: "#64748b", fontSize: 12, marginBottom: 6 }}>
            🔔 Auto-detected Events ({events.length})
          </div>
          <div style={{ maxHeight: 180, overflowY: "auto" }}>
            {events.slice(0, 8).map((ev, i) => <EventItem key={i} ev={ev} />)}
          </div>
        </div>
      )}
    </div>
  );
}

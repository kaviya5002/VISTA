interface ComponentData {
  component: string;
  health: number;
  failure_probability: number;
  rul: number;
  confidence: number;
  risk_color: string;
  status: string;
  trend?: { slope: number; direction: string; history: number[] };
}

interface Explanation {
  component: string;
  health: number;
  confidence: number;
  risk_color: string;
  reasons: string[];
}

interface Props {
  twin?: {
    vehicle_health: number;
    vehicle_status: string;
    critical_components: string[];
    battery: ComponentData;
    motor: ComponentData;
    cooling: ComponentData;
    brakes: ComponentData;
    electrical: ComponentData;
    transmission: ComponentData;
    explanations: Explanation[];
  };
  // legacy fallback props
  batteryHealth?: number;
  coolingHealth?: number;
  motorHealth?: number;
  transmissionHealth?: number;
}

const COMPONENT_ICONS: Record<string, string> = {
  Battery: "🔋",
  Motor: "⚙️",
  Cooling: "❄️",
  Brakes: "🛑",
  Electrical: "⚡",
  Transmission: "🔧",
};

const COMPONENT_KEYS = [
  "battery",
  "motor",
  "cooling",
  "brakes",
  "electrical",
  "transmission",
] as const;

function HealthBar({ value }: { value: number }) {
  const color = value >= 75 ? "#22c55e" : value >= 45 ? "#f97316" : "#ef4444";
  return (
    <div style={{ background: "#333", borderRadius: 4, height: 6, width: "100%", overflow: "hidden" }}>
      <div style={{ width: `${value}%`, background: color, height: "100%", transition: "width 0.4s" }} />
    </div>
  );
}

function TrendArrow({ direction }: { direction?: string }) {
  if (!direction) return null;
  if (direction === "Improving") return <span style={{ color: "#22c55e", fontSize: 12 }}>▲ Improving</span>;
  if (direction === "Degrading")  return <span style={{ color: "#ef4444", fontSize: 12 }}>▼ Degrading</span>;
  return <span style={{ color: "#9ca3af", fontSize: 12 }}>● Stable</span>;
}

function ComponentCard({ data, explain }: { data: ComponentData; explain?: Explanation }) {
  const icon = COMPONENT_ICONS[data.component] ?? "📦";
  return (
    <div style={{
      background: "#1e1e2e",
      borderRadius: 10,
      padding: "14px 16px",
      border: "1px solid #2a2a3d",
      display: "flex",
      flexDirection: "column",
      gap: 8,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>{icon} {data.component}</span>
        <span style={{ fontSize: 18 }}>{data.risk_color}</span>
      </div>

      <HealthBar value={data.health} />

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#9ca3af" }}>
        <span>Health <strong style={{ color: "#fff" }}>{data.health}%</strong></span>
        <span>RUL <strong style={{ color: "#fff" }}>{data.rul}d</strong></span>
        <span>Conf <strong style={{ color: "#fff" }}>{data.confidence}%</strong></span>
      </div>

      {data.trend && (
        <div style={{ fontSize: 12 }}>
          <TrendArrow direction={data.trend.direction} />
          {data.trend.history.length > 1 && (
            <span style={{ color: "#6b7280", marginLeft: 8 }}>
              slope {data.trend.slope > 0 ? "+" : ""}{data.trend.slope}
            </span>
          )}
        </div>
      )}

      {explain && explain.reasons.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: "#9ca3af" }}>
          {explain.reasons.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      )}
    </div>
  );
}

function DigitalTwin({ twin, batteryHealth, coolingHealth, motorHealth, transmissionHealth }: Props) {
  // Legacy fallback when full twin data not yet loaded
  if (!twin) {
    function getColor(v?: number) {
      if (!v) return "gray";
      return v > 80 ? "lime" : v > 50 ? "orange" : "red";
    }
    return (
      <div style={{ border: "2px solid gray", borderRadius: 12, padding: 20, width: 350, background: "#1a1a1a" }}>
        <h2>🚗 Digital Twin</h2>
        <p style={{ color: getColor(batteryHealth) }}>🔋 Battery: {batteryHealth}%</p>
        <p style={{ color: getColor(coolingHealth) }}>❄️ Cooling: {coolingHealth}%</p>
        <p style={{ color: getColor(motorHealth) }}>⚙️ Motor: {motorHealth}%</p>
        <p style={{ color: getColor(transmissionHealth) }}>🔧 Transmission: {transmissionHealth}%</p>
      </div>
    );
  }

  const explainMap = Object.fromEntries(
    twin.explanations.map((e) => [e.component, e])
  );

  const statusColor = twin.vehicle_status === "Healthy" ? "#22c55e"
    : twin.vehicle_status === "Warning" ? "#f97316" : "#ef4444";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Vehicle summary bar */}
      <div style={{
        background: "#1e1e2e",
        border: "1px solid #2a2a3d",
        borderRadius: 10,
        padding: "12px 16px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        <span style={{ fontWeight: 700, fontSize: 16 }}>🚗 Vehicle Twin</span>
        <span style={{ color: statusColor, fontWeight: 700 }}>{twin.vehicle_status}</span>
        <span style={{ color: "#9ca3af", fontSize: 14 }}>
          Overall <strong style={{ color: "#fff" }}>{twin.vehicle_health}%</strong>
        </span>
      </div>

      {twin.critical_components.length > 0 && (
        <div style={{
          background: "#2d1515",
          border: "1px solid #7f1d1d",
          borderRadius: 8,
          padding: "8px 12px",
          fontSize: 13,
          color: "#fca5a5",
        }}>
          🚨 Critical: {twin.critical_components.join(", ")}
        </div>
      )}

      {/* Component grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {COMPONENT_KEYS.map((key) => (
          <ComponentCard
            key={key}
            data={twin[key]}
            explain={explainMap[twin[key].component]}
          />
        ))}
      </div>
    </div>
  );
}

export default DigitalTwin;

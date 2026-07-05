import { useEffect, useState, useRef } from "react";
import api from "../services/api";

// ── Types ──────────────────────────────────────────────────────────────────
interface TimelineNode {
  day: number;
  title: string;
  date_label: string;
  health: number;
  failure: number;
  rul: number;
  status: string;
  status_color: string;
  priority: string;
  confidence: number;
  milestone: { type: string; label: string; color: string; icon: string } | null;
  narrative: string[];
  sensors: { temperature: number; battery_voltage: number; rpm: number };
  model: string;
  dataset: string;
}

interface ComponentData {
  vehicle_health: number;
  vehicle_status: string;
  component_scores: Record<string, number>;
  battery: { health: number; status: string };
  motor: { health: number; status: string };
  cooling: { health: number; status: string };
  brakes: { health: number; status: string };
  electrical: { health: number; status: string };
  transmission: { health: number; status: string };
}

interface TimelineData {
  vehicle_id: number;
  vehicle_name: string;
  timeline: TimelineNode[];
  summary: {
    current_status: string;
    current_health: number;
    current_failure: number;
    breakdown_day: number | null;
    first_critical_day: number | null;
    first_maintenance_day: number | null;
    overall_trend: string;
    health_at_day30: number;
    failure_at_day30: number;
  };
}

// ── Helpers ────────────────────────────────────────────────────────────────
const healthColor = (h: number) =>
  h >= 75 ? "#34D399" : h >= 45 ? "#FBBF24" : "#F87171";

const statusBg = (status: string) => ({
  Healthy:  { bg: "rgba(52,211,153,0.10)", border: "rgba(52,211,153,0.30)", dot: "#34D399" },
  Warning:  { bg: "rgba(251,191,36,0.10)",  border: "rgba(251,191,36,0.30)",  dot: "#FBBF24" },
  Critical: { bg: "rgba(248,113,113,0.10)", border: "rgba(248,113,113,0.30)", dot: "#F87171" },
}[status] ?? { bg: "rgba(100,116,139,0.10)", border: "rgba(100,116,139,0.30)", dot: "#64748B" });

const milestoneStyle = (type: string) => ({
  breakdown:   { bg: "rgba(239,68,68,0.15)",   border: "#EF4444", text: "#FCA5A5" },
  critical:    { bg: "rgba(249,115,22,0.15)",  border: "#F97316", text: "#FDBA74" },
  maintenance: { bg: "rgba(251,191,36,0.12)",  border: "#FBBF24", text: "#FDE68A" },
  health_drop: { bg: "rgba(167,139,250,0.12)", border: "#A78BFA", text: "#DDD6FE" },
  rul_critical:{ bg: "rgba(239,68,68,0.15)",   border: "#EF4444", text: "#FCA5A5" },
  rul_low:     { bg: "rgba(251,191,36,0.12)",  border: "#FBBF24", text: "#FDE68A" },
}[type] ?? { bg: "rgba(100,116,139,0.12)", border: "#64748B", text: "#94A3B8" });

// ── Mini gauge bar ─────────────────────────────────────────────────────────
function MiniBar({ value, color, label }: { value: number; color: string; label: string }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3, color: "#94A3B8" }}>
        <span>{label}</span>
        <span style={{ color, fontWeight: 700 }}>{value}%</span>
      </div>
      <div style={{ height: 4, background: "rgba(255,255,255,0.07)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{
          width: `${value}%`, height: "100%", background: color, borderRadius: 4,
          transition: "width 0.8s cubic-bezier(0.4,0,0.2,1)",
          boxShadow: `0 0 6px ${color}80`,
        }} />
      </div>
    </div>
  );
}

// ── Component scores panel (shown on node click) ───────────────────────────
function ComponentPanel({ vehicleId }: { vehicleId: number }) {
  const [data, setData] = useState<ComponentData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/component_twin/${vehicleId}`)
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [vehicleId]);

  if (loading) return (
    <div style={{ padding: "16px 0", color: "#475569", fontSize: 12, textAlign: "center" }}>
      Loading components…
    </div>
  );
  if (!data) return null;

  const components = [
    { key: "battery",      label: "Battery",      icon: "🔋" },
    { key: "motor",        label: "Motor",        icon: "⚙️" },
    { key: "cooling",      label: "Cooling",      icon: "❄️" },
    { key: "brakes",       label: "Brakes",       icon: "🛑" },
    { key: "electrical",   label: "Electrical",   icon: "⚡" },
    { key: "transmission", label: "Transmission", icon: "🔧" },
  ];

  return (
    <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid rgba(255,255,255,0.07)" }}>
      <div style={{ fontSize: 11, color: "#64748B", marginBottom: 10, fontWeight: 600, letterSpacing: "0.5px", textTransform: "uppercase" }}>
        Component Health
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 16px" }}>
        {components.map(({ key, label, icon }) => {
          const score = data.component_scores?.[label] ?? data[key as keyof ComponentData] as any;
          const health = typeof score === "number" ? score : score?.health ?? 0;
          const color = healthColor(health);
          return (
            <div key={key}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3 }}>
                <span style={{ color: "#94A3B8" }}>{icon} {label}</span>
                <span style={{ color, fontWeight: 700 }}>{health}%</span>
              </div>
              <div style={{ height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 3 }}>
                <div style={{
                  width: `${health}%`, height: "100%", background: color, borderRadius: 3,
                  transition: "width 0.8s ease",
                }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Single timeline node ───────────────────────────────────────────────────
function TimelineNode({
  node,
  index,
  vehicleId,
  isLast,
}: {
  node: TimelineNode;
  index: number;
  vehicleId: number;
  isLast: boolean;
}) {
  const [expanded, setExpanded] = useState(index === 0);
  const [visible, setVisible]   = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Staggered entrance animation
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), index * 120);
    return () => clearTimeout(t);
  }, [index]);

  const s       = statusBg(node.status);
  const ms      = node.milestone ? milestoneStyle(node.milestone.type) : null;
  const isToday = node.day === 0;

  return (
    <div
      ref={ref}
      style={{
        display: "flex",
        gap: 0,
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(16px)",
        transition: "opacity 0.45s ease, transform 0.45s ease",
      }}
    >
      {/* ── Left column: dot + connector line ── */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 40, flexShrink: 0 }}>
        {/* Dot */}
        <div
          onClick={() => setExpanded(e => !e)}
          style={{
            width: isToday ? 18 : 14,
            height: isToday ? 18 : 14,
            borderRadius: "50%",
            background: ms ? ms.border : s.dot,
            border: `2px solid ${ms ? ms.border : s.dot}`,
            boxShadow: `0 0 ${isToday ? 14 : 8}px ${ms ? ms.border : s.dot}80`,
            cursor: "pointer",
            flexShrink: 0,
            marginTop: 4,
            transition: "all 0.2s",
            zIndex: 1,
            position: "relative",
          }}
        />
        {/* Connector line */}
        {!isLast && (
          <div style={{
            width: 2,
            flex: 1,
            minHeight: 32,
            background: "linear-gradient(to bottom, " + s.dot + "60, rgba(255,255,255,0.04))",
            margin: "4px 0",
          }} />
        )}
      </div>

      {/* ── Right column: card ── */}
      <div style={{ flex: 1, paddingBottom: isLast ? 0 : 12, paddingLeft: 12 }}>

        {/* Card header — always visible */}
        <div
          onClick={() => setExpanded(e => !e)}
          style={{
            background: ms ? ms.bg : s.bg,
            border: `1px solid ${ms ? ms.border : s.border}`,
            borderRadius: 12,
            padding: "14px 16px",
            cursor: "pointer",
            transition: "all 0.2s",
            userSelect: "none",
          }}
          onMouseEnter={e => (e.currentTarget.style.transform = "translateX(3px)")}
          onMouseLeave={e => (e.currentTarget.style.transform = "translateX(0)")}
        >
          {/* Row 1: day label + status */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 800, color: "#F1F5F9" }}>
                  {isToday ? "● Today" : node.title}
                </span>
                {isToday && (
                  <span style={{
                    fontSize: 10, padding: "2px 7px", borderRadius: 10,
                    background: "rgba(56,189,248,0.15)", color: "#38BDF8",
                    fontWeight: 700, letterSpacing: "0.5px",
                  }}>LIVE</span>
                )}
              </div>
              <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>{node.date_label}</div>
            </div>

            {/* Status badge */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
              <span style={{
                fontSize: 11, padding: "3px 9px", borderRadius: 10, fontWeight: 700,
                background: s.bg, border: `1px solid ${s.border}`, color: s.dot,
              }}>{node.status}</span>
              {node.milestone && (
                <span style={{
                  fontSize: 10, padding: "2px 8px", borderRadius: 8, fontWeight: 700,
                  background: ms!.bg, border: `1px solid ${ms!.border}`, color: ms!.text,
                }}>
                  {node.milestone.icon} {node.milestone.label}
                </span>
              )}
            </div>
          </div>

          {/* Row 2: metrics */}
          <div style={{ display: "flex", gap: 20 }}>
            {[
              { label: "Health",  value: node.health,  suffix: "%", color: healthColor(node.health) },
              { label: "Failure", value: node.failure, suffix: "%", color: node.failure >= 60 ? "#F87171" : node.failure >= 35 ? "#FBBF24" : "#34D399" },
              { label: "RUL",     value: node.rul,     suffix: "d", color: node.rul <= 7 ? "#F87171" : node.rul <= 14 ? "#FBBF24" : "#34D399" },
            ].map(m => (
              <div key={m.label} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontWeight: 800, color: m.color, lineHeight: 1 }}>
                  {m.value}<span style={{ fontSize: 11 }}>{m.suffix}</span>
                </div>
                <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>{m.label}</div>
              </div>
            ))}

            {/* Confidence */}
            <div style={{ textAlign: "center", marginLeft: "auto" }}>
              <div style={{ fontSize: 13, fontWeight: 800, color: "#A78BFA", lineHeight: 1 }}>
                {node.confidence}%
              </div>
              <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>Confidence</div>
            </div>
          </div>
        </div>

        {/* ── Expanded detail panel ── */}
        {expanded && (
          <div style={{
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.05)",
            borderTop: "none",
            borderRadius: "0 0 12px 12px",
            padding: "14px 16px",
            marginTop: -1,
          }}>
            {/* Gauge bars */}
            <MiniBar value={node.health}  color={healthColor(node.health)}  label="Health Score" />
            <MiniBar
              value={node.failure}
              color={node.failure >= 60 ? "#F87171" : node.failure >= 35 ? "#FBBF24" : "#34D399"}
              label="Failure Risk"
            />

            {/* Sensor snapshot */}
            <div style={{ display: "flex", gap: 12, marginTop: 12, marginBottom: 12 }}>
              {[
                { label: "Temp",    value: `${node.sensors.temperature}°C` },
                { label: "Voltage", value: `${node.sensors.battery_voltage}V` },
                { label: "RPM",     value: `${node.sensors.rpm}` },
              ].map(s => (
                <div key={s.label} style={{
                  flex: 1, textAlign: "center", padding: "6px 8px",
                  background: "rgba(255,255,255,0.03)", borderRadius: 8,
                  border: "1px solid rgba(255,255,255,0.06)",
                }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#F1F5F9" }}>{s.value}</div>
                  <div style={{ fontSize: 10, color: "#475569" }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* AI narrative */}
            {node.narrative.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                {node.narrative.map((line, i) => (
                  <div key={i} style={{
                    fontSize: 12, color: "#94A3B8", lineHeight: 1.5,
                    padding: "3px 0 3px 10px",
                    borderLeft: "2px solid rgba(167,139,250,0.3)",
                    marginBottom: 4,
                  }}>
                    {line}
                  </div>
                ))}
              </div>
            )}

            {/* Model badge */}
            <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
              <span style={{
                fontSize: 10, padding: "2px 8px", borderRadius: 8,
                background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.2)",
                color: "#38BDF8",
              }}>
                🤖 {node.model}
              </span>
              <span style={{
                fontSize: 10, padding: "2px 8px", borderRadius: 8,
                background: "rgba(167,139,250,0.08)", border: "1px solid rgba(167,139,250,0.2)",
                color: "#A78BFA",
              }}>
                📊 {node.dataset}
              </span>
              <span style={{
                fontSize: 10, padding: "2px 8px", borderRadius: 8,
                background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.2)",
                color: "#34D399",
              }}>
                {node.confidence}% confidence
              </span>
            </div>

            {/* Component health — only shown on Today node */}
            {isToday && <ComponentPanel vehicleId={vehicleId} />}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Summary bar at the top ─────────────────────────────────────────────────
function TimelineSummary({ summary, vehicleName }: { summary: TimelineData["summary"]; vehicleName: string }) {
  const trendColor = summary.overall_trend.includes("Rapidly") ? "#F87171"
    : summary.overall_trend.includes("Degrading") ? "#FBBF24" : "#34D399";

  return (
    <div style={{
      background: "rgba(255,255,255,0.02)",
      border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: 12,
      padding: "16px 20px",
      marginBottom: 24,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#F1F5F9", marginBottom: 4 }}>
            🔮 AI Forecast — {vehicleName}
          </div>
          <div style={{ fontSize: 12, color: "#64748B" }}>
            30-day predictive journey · Random Forest + NASA CMAPSS
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: trendColor }}>{summary.overall_trend}</div>
            <div style={{ fontSize: 10, color: "#475569" }}>Trend</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#F87171" }}>
              {summary.breakdown_day ? `Day ${summary.breakdown_day}` : "Not Predicted"}
            </div>
            <div style={{ fontSize: 10, color: "#475569" }}>Breakdown</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#FBBF24" }}>
              {summary.first_maintenance_day ? `Day ${summary.first_maintenance_day}` : "—"}
            </div>
            <div style={{ fontSize: 10, color: "#475569" }}>1st Maintenance</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: healthColor(summary.health_at_day30) }}>
              {summary.health_at_day30}%
            </div>
            <div style={{ fontSize: 10, color: "#475569" }}>Health @ Day 30</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main exported component ────────────────────────────────────────────────
export default function VehicleTimeline({ vehicleId }: { vehicleId: number }) {
  const [data,    setData]    = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    api.get(`/vehicle/${vehicleId}/timeline`)
      .then(r  => { setData(r.data); setLoading(false); })
      .catch(() => { setError(true);  setLoading(false); });
  }, [vehicleId]);

  if (loading) return (
    <div style={{
      padding: "40px 0", textAlign: "center",
      color: "#475569", fontSize: 13,
    }}>
      <div style={{
        width: 32, height: 32, border: "3px solid rgba(56,189,248,0.3)",
        borderTop: "3px solid #38BDF8", borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
        margin: "0 auto 12px",
      }} />
      Generating AI timeline…
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (error || !data) return (
    <div style={{
      padding: "24px", textAlign: "center",
      color: "#F87171", fontSize: 12,
      background: "rgba(248,113,113,0.06)",
      border: "1px solid rgba(248,113,113,0.2)",
      borderRadius: 10,
    }}>
      ⚠️ Timeline unavailable — backend may be offline.
    </div>
  );

  return (
    <div>
      <TimelineSummary summary={data.summary} vehicleName={data.vehicle_name} />
      <div style={{ position: "relative" }}>
        {data.timeline.map((node, i) => (
          <TimelineNode
            key={node.day}
            node={node}
            index={i}
            vehicleId={vehicleId}
            isLast={i === data.timeline.length - 1}
          />
        ))}
      </div>
    </div>
  );
}

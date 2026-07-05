import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useFleetSocket } from "../hooks/useFleetSocket";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { statusColor, healthColor } from "../hooks/useCounter";
import Navbar from "../components/Navbar";
import HealthRing from "../components/HealthRing";
import FleetHeatmap from "../components/FleetHeatmap";
import AIInsights from "../components/AIInsights";
import StatCard from "../components/StatCard";
import { CACHE_TTL } from "../store/fleetStore";

const API = "http://127.0.0.1:8001";

export default function Dashboard() {
  const { fleetMap, connected } = useFleetSocket();

  // /dashboard — fast pure-DB summary, arrives in ~5ms
  const { data: summary } = useAutoRefresh<any>("dashboard", "/dashboard", CACHE_TTL.alerts);

  // Fetch /fleet immediately on mount — don't wait for WS
  const [baseVehicles, setBaseVehicles] = useState<any[]>([]);
  const fetchedRef = useRef(false);
  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    fetch(`${API}/fleet`)
      .then(r => r.json())
      .then(d => setBaseVehicles(Array.isArray(d) ? d : []))
      .catch(() => {});
  }, []);

  // Merge WS live sensor values onto base HTTP enriched data
  const merged = useMemo(() => {
    if (!baseVehicles.length) return [];
    if (!fleetMap.size) return baseVehicles;
    return baseVehicles.map(b => {
      const live = fleetMap.get(b.vehicle_id);
      if (!live) return b;
      return {
        ...b,
        health_score: live.health,
        failure_probability: live.failure_probability,
        temperature: live.temperature,
        battery_voltage: live.battery_voltage,
        rpm: live.rpm,
        remaining_useful_life_days: live.rul,
        status: live.status,
      };
    });
  }, [baseVehicles, fleetMap]);

  const loading = baseVehicles.length === 0;

  // Counts — use merged when available, fall back to /dashboard summary
  const total    = merged.length    || summary?.total    || 0;
  const healthy  = merged.length ? merged.filter(v => v.status === "Healthy").length  : (summary?.healthy  ?? 0);
  const warning  = merged.length ? merged.filter(v => v.status === "Warning").length  : (summary?.warning  ?? 0);
  const critical = merged.length ? merged.filter(v => v.status === "Critical").length : (summary?.critical ?? 0);
  const alerts   = summary?.alerts ?? [];

  const avgHealth = total ? Math.round(merged.reduce((s, v) => s + (v.health_score ?? 0), 0) / total) : 0;
  const avgRisk   = total ? Math.round(merged.reduce((s, v) => s + (v.failure_probability ?? 0), 0) / total) : 0;

  const totalSavings    = merged.reduce((s, v) => s + (v.potential_savings ?? 0), 0);
  const failingWeek     = merged.filter(v => (v.remaining_useful_life_days ?? 99) <= 7).length;
  const immediateRepair = merged.filter(v => v.fleet_action === "Immediate Repair" || v.fleet_action === "Repair Immediately").length;
  const downtimePrev    = critical * 4 + warning;
  const topPriority     = [...merged].sort((a, b) => (b.priority_score ?? 0) - (a.priority_score ?? 0)).slice(0, 8);

  return (
    <div style={{ background: "#05070A", minHeight: "100vh", paddingTop: 56 }}>
      <Navbar connected={connected} />

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 32px 64px" }}>

        {/* ── HERO ── */}
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <div style={{
            display: "inline-block", padding: "4px 14px", borderRadius: 20, marginBottom: 16,
            background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.2)",
            fontSize: 12, color: "#38BDF8", letterSpacing: "1px", textTransform: "uppercase",
          }}>
            {connected ? "⬤ Live Feed Active" : "⬤ Connecting…"}
          </div>
          <h1 style={{
            fontSize: "clamp(28px,4vw,52px)", fontWeight: 900,
            background: "linear-gradient(135deg,#F1F5F9 30%,#38BDF8 70%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            letterSpacing: "-2px", lineHeight: 1.1, marginBottom: 12,
          }}>VISTA AI</h1>
          <p style={{ color: "#64748B", fontSize: 15, marginBottom: 32 }}>
            Intelligent Fleet Command Center — {total} Vehicles Connected
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            {[
              { label: "Healthy",  val: healthy,  color: "#34D399" },
              { label: "Warning",  val: warning,  color: "#FBBF24" },
              { label: "Critical", val: critical, color: "#F87171" },
            ].map(s => (
              <div key={s.label} style={{
                padding: "8px 20px", borderRadius: 24,
                background: s.color + "14", border: `1px solid ${s.color}44`,
                color: s.color, fontWeight: 700, fontSize: 14,
                display: "flex", alignItems: "center", gap: 8,
              }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: s.color, boxShadow: `0 0 8px ${s.color}`, display: "inline-block" }} />
                {s.val} {s.label}
              </div>
            ))}
          </div>
        </div>

        {/* ── TOP METRICS ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12, marginBottom: 32 }}>
          <StatCard label="Total Vehicles"     value={total}           color="#38BDF8" />
          <StatCard label="Avg Fleet Health"   value={avgHealth}       color={healthColor(avgHealth)} suffix="%" />
          <StatCard label="Avg Failure Risk"   value={avgRisk}         color={avgRisk > 60 ? "#F87171" : "#FBBF24"} suffix="%" />
          <StatCard label="Failing This Week"  value={failingWeek}     color="#F87171" sub="RUL ≤ 7 days" />
          <StatCard label="Immediate Repairs"  value={immediateRepair} color="#FBBF24" />
          <StatCard label="Downtime Prevented" value={downtimePrev}    color="#34D399" suffix=" hrs" />
          <StatCard label="Active Alerts"      value={alerts.length}   color="#F87171" />
          <StatCard label="Potential Savings"  value={Math.round(totalSavings / 1000)} color="#34D399" prefix="₹" suffix="K" />
        </div>

        {/* Nav links */}
        <div style={{ marginBottom: 24, display: "flex", gap: 12, flexWrap: "wrap" }}>
          {[
            { to: "/replay",      bg: "rgba(124,58,237,0.12)", border: "rgba(124,58,237,0.3)", color: "#a78bfa", label: "⏱ Fleet Replay — Watch 24h History" },
            { to: "/calendar",    bg: "rgba(56,189,248,0.10)", border: "rgba(56,189,248,0.3)", color: "#38BDF8", label: "🗓 AI Maintenance Calendar" },
            { to: "/technicians", bg: "rgba(52,211,153,0.10)", border: "rgba(52,211,153,0.3)", color: "#34D399", label: "👨‍🔧 Technician Assignment" },
          ].map(l => (
            <Link key={l.to} to={l.to} style={{
              display: "inline-flex", alignItems: "center", gap: 8, padding: "10px 20px", borderRadius: 10,
              background: l.bg, border: `1px solid ${l.border}`, color: l.color,
              textDecoration: "none", fontWeight: 600, fontSize: 13,
            }}>{l.label}</Link>
          ))}
        </div>

        {/* ── MAIN GRID ── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20, marginBottom: 24 }}>

          {/* Live Fleet Data */}
          <div className="glass" style={{ padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <div>
                <h2 style={{ fontSize: 16, marginBottom: 2 }}>🗺️ Live Fleet Data</h2>
                <p style={{ fontSize: 12, color: "#64748B" }}>
                  {loading ? "Loading fleet data…" : `${total} vehicles · ${connected ? "Live WS updates" : "HTTP data"} · Click to open twin`}
                </p>
              </div>
              <div style={{ display: "flex", gap: 12, fontSize: 12 }}>
                {[["#34D399","Healthy"],["#FBBF24","Warning"],["#F87171","Critical"]].map(([c,l]) => (
                  <span key={l} style={{ color: c, display: "flex", alignItems: "center", gap: 4 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: c, display: "inline-block" }} /> {l}
                  </span>
                ))}
              </div>
            </div>
            {loading ? (
              <div style={{ height: 200, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: "#334155" }}>
                <div style={{ width: 32, height: 32, border: "3px solid #38BDF822", borderTop: "3px solid #38BDF8", borderRadius: "50%", animation: "spin 1s linear infinite" }} />
                <span style={{ fontSize: 13 }}>Fetching fleet data…</span>
              </div>
            ) : (
              <FleetHeatmap vehicles={merged} />
            )}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Fleet Health */}
            <div className="glass" style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
              <h2 style={{ fontSize: 15, alignSelf: "flex-start" }}>⚡ Fleet Health</h2>
              {loading ? (
                <div style={{ height: 180, display: "flex", alignItems: "center", justifyContent: "center", color: "#334155", fontSize: 13 }}>
                  Loading…
                </div>
              ) : (
                <>
                  <HealthRing value={avgHealth} size={180} />
                  <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
                    {[
                      { label: "Healthy",  val: healthy,  pct: total ? Math.round(healthy/total*100)  : 0, color: "#34D399" },
                      { label: "Warning",  val: warning,  pct: total ? Math.round(warning/total*100)  : 0, color: "#FBBF24" },
                      { label: "Critical", val: critical, pct: total ? Math.round(critical/total*100) : 0, color: "#F87171" },
                    ].map(row => (
                      <div key={row.label}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
                          <span style={{ color: "#64748B" }}>{row.label}</span>
                          <span style={{ color: row.color, fontWeight: 600 }}>{row.val} ({row.pct}%)</span>
                        </div>
                        <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 4 }}>
                          <div style={{ width: `${row.pct}%`, height: "100%", background: row.color, borderRadius: 4, transition: "width 1s" }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            <div className="glass" style={{ padding: 20 }}>
              <h2 style={{ fontSize: 14, marginBottom: 12, color: "#34D399" }}>💰 Business Impact</h2>
              {[
                { label: "Potential Savings",  val: `₹${totalSavings.toLocaleString("en-IN")}`, color: "#34D399" },
                { label: "Failures Prevented", val: `${critical + warning}`,                    color: "#38BDF8" },
                { label: "Downtime Prevented", val: `${downtimePrev} hrs`,                      color: "#A78BFA" },
              ].map(r => (
                <div key={r.label} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.05)", fontSize: 13 }}>
                  <span style={{ color: "#64748B" }}>{r.label}</span>
                  <span style={{ color: r.color, fontWeight: 700 }}>{r.val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── AI INSIGHTS + PRIORITY ── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>

          {/* AI Fleet Intelligence */}
          <div className="glass" style={{ padding: 24 }}>
            <h2 style={{ fontSize: 16, marginBottom: 4 }}>🧠 AI Fleet Intelligence</h2>
            <p style={{ fontSize: 12, color: "#64748B", marginBottom: 20 }}>Real-time predictions from 5 ML models</p>
            {loading ? (
              <AIInsightsLoading />
            ) : (
              <AIInsights vehicles={merged} critical={critical} avgHealth={avgHealth} totalSavings={totalSavings} />
            )}
          </div>

          {/* AI Priority Ranking */}
          <div className="glass" style={{ padding: 24 }}>
            <h2 style={{ fontSize: 16, marginBottom: 4 }}>🔥 AI Priority Ranking</h2>
            <p style={{ fontSize: 12, color: "#64748B", marginBottom: 20 }}>Fleet Optimizer ML — sorted by urgency</p>
            {loading ? (
              <PriorityLoading />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {topPriority.map((v, i) => (
                  <Link key={v.vehicle_id} to={`/vehicle/${v.vehicle_id}`}>
                    <div style={{
                      display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", borderRadius: 10,
                      background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", transition: "all 0.15s",
                    }}
                      onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.02)")}
                    >
                      <span style={{ fontSize: 11, color: "#334155", fontWeight: 700, minWidth: 22 }}>#{i + 1}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>Vehicle {v.vehicle_id}</div>
                        <div style={{ fontSize: 11, color: "#475569" }}>
                          RUL {v.remaining_useful_life_days ?? v.rul}d · {v.fleet_action ?? v.status}
                        </div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: healthColor(v.health_score ?? v.health) }}>
                          {v.health_score ?? v.health}%
                        </div>
                        <div style={{ fontSize: 11, color: statusColor(v.status) }}>{v.status}</div>
                      </div>
                      <div style={{ width: 48, height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 4 }}>
                        <div style={{ width: `${v.health_score ?? v.health}%`, height: "100%", background: healthColor(v.health_score ?? v.health), borderRadius: 4 }} />
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── CRITICAL ALERTS ── */}
        {alerts.length > 0 && (
          <div className="glass" style={{ padding: 24 }}>
            <h2 style={{ fontSize: 16, marginBottom: 20 }}>🚨 Active Alerts</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: 12 }}>
              {alerts.slice(0, 6).map((a: any, i: number) => (
                <Link key={i} to={`/vehicle/${a.vehicle_id}`}>
                  <div style={{
                    padding: "14px 16px", borderRadius: 12,
                    background: a.severity === "Critical" ? "rgba(248,113,113,0.06)" : "rgba(251,191,36,0.06)",
                    border: `1px solid ${a.severity === "Critical" ? "rgba(248,113,113,0.3)" : "rgba(251,191,36,0.3)"}`,
                    transition: "all 0.15s",
                    animation: a.severity === "Critical" ? "alertPulse 2s infinite" : "none",
                  }}
                    onMouseEnter={e => (e.currentTarget.style.transform = "translateY(-2px)")}
                    onMouseLeave={e => (e.currentTarget.style.transform = "translateY(0)")}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontWeight: 700, fontSize: 13, color: a.severity === "Critical" ? "#F87171" : "#FBBF24" }}>
                        {a.alert_type}
                      </span>
                      <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 10,
                        background: a.severity === "Critical" ? "rgba(248,113,113,0.15)" : "rgba(251,191,36,0.15)",
                        color: a.severity === "Critical" ? "#F87171" : "#FBBF24",
                      }}>{a.severity}</span>
                    </div>
                    <p style={{ fontSize: 12, color: "#94A3B8", marginBottom: 6 }}>Vehicle {a.vehicle_id} · {a.message}</p>
                    <p style={{ fontSize: 12, color: "#38BDF8" }}>→ {a.action}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes alertPulse {
          0%,100% { border-color: rgba(248,113,113,0.3); }
          50%      { border-color: rgba(248,113,113,0.7); }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes shimmer {
          0%   { background-position: -400px 0; }
          100% { background-position: 400px 0; }
        }
        .skeleton {
          background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%);
          background-size: 400px 100%;
          animation: shimmer 1.4s infinite;
          border-radius: 8px;
        }
      `}</style>
    </div>
  );
}

function AIInsightsLoading() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {[...Array(6)].map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 56, borderRadius: 10 }} />
      ))}
    </div>
  );
}

function PriorityLoading() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {[...Array(8)].map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 48, borderRadius: 10 }} />
      ))}
    </div>
  );
}

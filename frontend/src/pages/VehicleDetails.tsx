import { useEffect, useState, lazy, Suspense, useRef } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../services/api";
import { getCached, setCached, CACHE_TTL } from "../store/fleetStore";

// Lazy — each tab's bundle is fetched only when first opened
const FailurePropagation  = lazy(() => import("../components/FailurePropagation"));
const VehicleTimeline     = lazy(() => import("../components/VehicleTimeline"));
const SHAPExplanationCard = lazy(() => import("../components/SHAPExplanationCard"));
const VehicleDigitalTwin  = lazy(() => import("../components/VehicleDigitalTwin"));

// ── Helpers ────────────────────────────────────────────────────────────────
const healthColor = (h: number) =>
  h >= 75 ? "#34D399" : h >= 45 ? "#FBBF24" : "#F87171";

const statusColor = (s: string) =>
  s === "Healthy" ? "#34D399" : s === "Warning" ? "#FBBF24" : "#F87171";

function StatRow({ icon, label, value, color }: { icon: string; label: string; value: any; color?: string }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "10px 0",
      borderBottom: "1px solid rgba(255,255,255,0.05)",
    }}>
      <span style={{ fontSize: 13, color: "#64748B" }}>{icon} {label}</span>
      <span style={{ fontSize: 13, fontWeight: 700, color: color ?? "#F1F5F9" }}>{value}</span>
    </div>
  );
}

const TabFallback = () => (
  <div style={{ padding: "40px 0", textAlign: "center", color: "#475569", fontSize: 13 }}>
    <div style={{
      width: 28, height: 28, border: "3px solid rgba(56,189,248,0.3)",
      borderTop: "3px solid #38BDF8", borderRadius: "50%",
      animation: "spin 0.8s linear infinite", margin: "0 auto 12px",
    }} />
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </div>
);

// ── Tab nav ────────────────────────────────────────────────────────────────
const TABS = [
  { id: "overview",  label: "Overview",      icon: "📊" },
  { id: "xai",       label: "AI Explanation", icon: "🧠" },
  { id: "timeline",  label: "AI Timeline",   icon: "🔮" },
  { id: "twin",      label: "Digital Twin",  icon: "⚙️" },
  { id: "chain",     label: "Propagation",   icon: "⚡" },
];

export default function VehicleDetails() {
  const { id }      = useParams();
  const navigate    = useNavigate();
  const [vehicle, setVehicle]   = useState<any>(null);
  const [activeTab, setActiveTab] = useState("overview");
  // Track which tabs have ever been opened — keep them mounted once visited
  const visited = useRef<Set<string>>(new Set(["overview"]));

  function openTab(tab: string) {
    visited.current.add(tab);
    setActiveTab(tab);
  }

  useEffect(() => {
    const cacheKey = `vehicle_${id}`;
    const cached = getCached<any>(cacheKey, CACHE_TTL.vehicle);
    if (cached) { setVehicle(cached); return; }
    api.get(`/vehicle/${id}`)
      .then(r => { setCached(cacheKey, r.data); setVehicle(r.data); })
      .catch(console.error);
  }, [id]);

  if (!vehicle) return (
    <div style={{
      minHeight: "100vh", background: "#05070A",
      display: "flex", alignItems: "center", justifyContent: "center",
      color: "#475569", fontSize: 14,
    }}>
      <div>
        <div style={{
          width: 36, height: 36, border: "3px solid rgba(56,189,248,0.3)",
          borderTop: "3px solid #38BDF8", borderRadius: "50%",
          animation: "spin 0.8s linear infinite", margin: "0 auto 12px",
        }} />
        Loading vehicle {id}…
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  const sc  = statusColor(vehicle.status);
  const vid = Number(id);

  return (
    <div style={{ background: "#05070A", minHeight: "100vh", paddingTop: 64 }}>

      {/* ── Top nav bar ── */}
      <div style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        background: "rgba(5,7,10,0.9)", backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "0 32px", height: 56,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Link to="/" style={{
            color: "#64748B", fontSize: 13, textDecoration: "none",
            display: "flex", alignItems: "center", gap: 6,
          }}>
            ← Fleet
          </Link>
          <span style={{ color: "#1E293B" }}>|</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#F1F5F9" }}>
            Vehicle {vid}
          </span>
          <span style={{
            fontSize: 11, padding: "2px 9px", borderRadius: 10,
            background: sc + "18", border: `1px solid ${sc}44`, color: sc,
            fontWeight: 700,
          }}>{vehicle.status}</span>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <a
            href={`http://127.0.0.1:8001/report/${vid}`}
            target="_blank" rel="noreferrer"
            style={{
              fontSize: 12, padding: "6px 14px", borderRadius: 8,
              background: "rgba(251,191,36,0.1)", border: "1px solid rgba(251,191,36,0.3)",
              color: "#FBBF24", textDecoration: "none", fontWeight: 600,
            }}
          >📄 Report</a>
          <Link
            to={`/workorder/${vid}`}
            style={{
              fontSize: 12, padding: "6px 14px", borderRadius: 8,
              background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.3)",
              color: "#34D399", textDecoration: "none", fontWeight: 600,
            }}
          >🗒 Work Order</Link>
          <button
            onClick={() => navigate(`/simulate?vehicle_id=${vid}`)}
            style={{
              fontSize: 12, padding: "6px 14px", borderRadius: 8,
              background: "rgba(124,58,237,0.15)", border: "1px solid rgba(124,58,237,0.3)",
              color: "#A78BFA", cursor: "pointer", fontWeight: 600,
            }}
          >🔮 Simulator</button>
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 32px 80px" }}>

        {/* ── Hero header ── */}
        <div style={{
          display: "grid", gridTemplateColumns: "1fr auto",
          gap: 20, alignItems: "center", marginBottom: 28,
        }}>
          <div>
            <h1 style={{
              fontSize: 32, fontWeight: 900, letterSpacing: "-1.5px",
              background: "linear-gradient(135deg, #F1F5F9 40%, #38BDF8 80%)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              marginBottom: 8,
            }}>
              Vehicle {vid}
            </h1>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              {[
                { label: `Health ${vehicle.health_score}%`,           color: healthColor(vehicle.health_score) },
                { label: `Failure ${vehicle.failure_probability}%`,    color: vehicle.failure_probability > 60 ? "#F87171" : "#FBBF24" },
                { label: `RUL ${vehicle.remaining_useful_life_days}d`, color: vehicle.remaining_useful_life_days <= 7 ? "#F87171" : "#34D399" },
                { label: vehicle.failure_risk + " Risk",               color: vehicle.failure_risk === "High" ? "#F87171" : vehicle.failure_risk === "Medium" ? "#FBBF24" : "#34D399" },
              ].map(p => (
                <span key={p.label} style={{
                  fontSize: 12, padding: "4px 12px", borderRadius: 20,
                  background: p.color + "14", border: `1px solid ${p.color}40`,
                  color: p.color, fontWeight: 700,
                }}>{p.label}</span>
              ))}
            </div>
          </div>

          {/* Confidence ring */}
          <div style={{ textAlign: "center" }}>
            <div style={{
              width: 72, height: 72, borderRadius: "50%",
              background: `conic-gradient(#A78BFA ${vehicle.confidence_score ?? 88}%, rgba(255,255,255,0.06) 0)`,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <div style={{
                width: 58, height: 58, borderRadius: "50%",
                background: "#05070A",
                display: "flex", alignItems: "center", justifyContent: "center",
                flexDirection: "column",
              }}>
                <span style={{ fontSize: 16, fontWeight: 800, color: "#A78BFA" }}>
                  {vehicle.confidence_score ?? 88}%
                </span>
              </div>
            </div>
            <div style={{ fontSize: 10, color: "#475569", marginTop: 6 }}>AI Confidence</div>
          </div>
        </div>

        {/* ── Tab navigation ── */}
        <div style={{
          display: "flex", gap: 4, marginBottom: 24,
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 12, padding: 4,
          width: "fit-content",
        }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => openTab(tab.id)}
              style={{
                padding: "8px 18px", borderRadius: 9,
                background: activeTab === tab.id ? "rgba(56,189,248,0.12)" : "transparent",
                color: activeTab === tab.id ? "#38BDF8" : "#475569",
                fontSize: 13, fontWeight: activeTab === tab.id ? 700 : 400,
                cursor: "pointer",
                border: activeTab === tab.id
                  ? "1px solid rgba(56,189,248,0.25)"
                  : "1px solid transparent",
                transition: "all 0.15s",
              }}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* ── Tab content ── */}

        {/* Overview — always mounted, no lazy needed */}
        <div style={{ display: activeTab === "overview" ? "block" : "none" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <div className="glass" style={{ padding: 24 }}>
              <h2 style={{ fontSize: 15, marginBottom: 16, color: "#38BDF8" }}>📊 Vehicle Diagnostics</h2>
              <StatRow icon="🔋" label="Health Score"        value={`${vehicle.health_score}%`}             color={healthColor(vehicle.health_score)} />
              <StatRow icon="⚠️" label="Failure Probability" value={`${vehicle.failure_probability}%`}       color={vehicle.failure_probability > 60 ? "#F87171" : "#FBBF24"} />
              <StatRow icon="📅" label="Remaining Useful Life" value={`${vehicle.remaining_useful_life_days} days`} color={vehicle.remaining_useful_life_days <= 7 ? "#F87171" : "#34D399"} />
              <StatRow icon="🌡️" label="Temperature"          value={`${vehicle.temperature}°C`}            color={vehicle.temperature > 80 ? "#F87171" : vehicle.temperature > 60 ? "#FBBF24" : "#34D399"} />
              <StatRow icon="🔌" label="Battery Voltage"      value={`${vehicle.battery_voltage}V`}          color={vehicle.battery_voltage < 11.0 ? "#F87171" : vehicle.battery_voltage < 12.0 ? "#FBBF24" : "#34D399"} />
              <StatRow icon="⚙️" label="RPM"                  value={vehicle.rpm}                            color={vehicle.rpm > 5000 ? "#F87171" : vehicle.rpm > 3500 ? "#FBBF24" : "#34D399"} />
              <StatRow icon="🚗" label="Speed"                value={`${vehicle.speed} km/h`} />
            </div>

            <div className="glass" style={{ padding: 24 }}>
              <h2 style={{ fontSize: 15, marginBottom: 16, color: "#A78BFA" }}>🧠 AI Recommendation</h2>
              <StatRow icon="🛠️" label="Fleet Action"    value={vehicle.fleet_action}                  color="#FBBF24" />
              <StatRow icon="💡" label="Recommendation"  value={vehicle.maintenance_recommendation}     color="#38BDF8" />
              <StatRow icon="📊" label="Confidence"      value={`${vehicle.confidence_score}%`}         color="#A78BFA" />
              <StatRow icon="🔍" label="Root Cause"      value={vehicle.root_cause?.join(", ") || "None"} />
              <StatRow icon="🚨" label="Risk Level"      value={vehicle.estimated_risk ?? vehicle.risk_level} color={vehicle.estimated_risk === "Critical" ? "#F87171" : vehicle.estimated_risk === "High" ? "#FBBF24" : "#34D399"} />
              <StatRow icon="🕒" label="Next Service"    value={vehicle.next_service ?? "—"} />
              <div style={{ marginTop: 16, padding: "12px 16px", borderRadius: 10, background: "rgba(167,139,250,0.06)", border: "1px solid rgba(167,139,250,0.15)" }}>
                <div style={{ fontSize: 11, color: "#64748B", marginBottom: 6 }}>AI Reasoning</div>
                {(vehicle.reasoning ?? []).slice(0, 3).map((r: string, i: number) => (
                  <div key={i} style={{ fontSize: 12, color: "#94A3B8", lineHeight: 1.5, paddingLeft: 8, borderLeft: "2px solid rgba(167,139,250,0.3)", marginBottom: 4 }}>
                    {r}
                  </div>
                ))}
              </div>
            </div>

            <div className="glass" style={{ padding: 24 }}>
              <h2 style={{ fontSize: 15, marginBottom: 16, color: "#34D399" }}>💰 Financial Impact</h2>
              <StatRow icon="🔧" label="Repair Now Cost"   value={`₹${vehicle.repair_now_cost?.toLocaleString("en-IN")}`}  color="#FBBF24" />
              <StatRow icon="💥" label="Failure Cost"      value={`₹${vehicle.failure_cost?.toLocaleString("en-IN")}`}     color="#F87171" />
              <StatRow icon="✅" label="Potential Savings" value={`₹${vehicle.potential_savings?.toLocaleString("en-IN")}`} color="#34D399" />
              <StatRow icon="⏱️" label="Downtime Prevented" value={`${vehicle.business_impact?.downtime_prevented_hours ?? "—"} hrs`} color="#38BDF8" />
            </div>

            <div className="glass" style={{ padding: 24 }}>
              <h2 style={{ fontSize: 15, marginBottom: 16, color: "#FBBF24" }}>🔥 Priority Score</h2>
              <div style={{ textAlign: "center", padding: "20px 0" }}>
                <div style={{ fontSize: 52, fontWeight: 900, color: vehicle.priority_score > 100 ? "#F87171" : "#FBBF24", lineHeight: 1 }}>
                  {vehicle.priority_score ?? "—"}
                </div>
                <div style={{ fontSize: 12, color: "#64748B", marginTop: 8 }}>Composite Priority Score</div>
              </div>
              <StatRow icon="📌" label="Priority"  value={vehicle.priority}               color="#FBBF24" />
              <StatRow icon="🏃" label="Action"    value={vehicle.fleet_action}           color="#F87171" />
              <StatRow icon="⚡" label="Est. Risk" value={vehicle.estimated_risk ?? "—"} color={vehicle.estimated_risk === "Critical" ? "#F87171" : "#FBBF24"} />
            </div>
          </div>
        </div>

        {/* AI Explanation — lazy, mounted on first visit */}
        {visited.current.has("xai") && (
          <div style={{ display: activeTab === "xai" ? "block" : "none" }}>
            <Suspense fallback={<TabFallback />}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                <SHAPExplanationCard vehicleId={vid} />
                <div className="glass" style={{ padding: 24 }}>
                  <h2 style={{ fontSize: 15, marginBottom: 16, color: "#38BDF8" }}>📊 Model Feature Importances</h2>
                  <p style={{ fontSize: 12, color: "#64748B", marginBottom: 16 }}>
                    General feature weights across all training data (not vehicle-specific)
                  </p>
                  <a
                    href={`http://127.0.0.1:8001/xai/features/${vid}`}
                    target="_blank" rel="noreferrer"
                    style={{
                      display: "inline-block", padding: "8px 16px", borderRadius: 8,
                      background: "rgba(56,189,248,0.1)", border: "1px solid rgba(56,189,248,0.3)",
                      color: "#38BDF8", textDecoration: "none", fontSize: 12, fontWeight: 600,
                    }}
                  >
                    View Raw Feature Importances JSON →
                  </a>
                </div>
              </div>
            </Suspense>
          </div>
        )}

        {/* AI Timeline — lazy, mounted on first visit */}
        {visited.current.has("timeline") && (
          <div style={{ display: activeTab === "timeline" ? "block" : "none" }}>
            <Suspense fallback={<TabFallback />}>
              <div className="glass" style={{ padding: 28 }}>
                <VehicleTimeline vehicleId={vid} />
              </div>
            </Suspense>
          </div>
        )}

        {/* Digital Twin — lazy, mounted on first visit */}
        {visited.current.has("twin") && (
          <div style={{ display: activeTab === "twin" ? "block" : "none" }}>
            <Suspense fallback={<TabFallback />}>
              <VehicleDigitalTwin vehicleId={vid} />
            </Suspense>
          </div>
        )}

        {/* Failure Propagation Engine — lazy, mounted on first visit */}
        {visited.current.has("chain") && (
          <div style={{ display: activeTab === "chain" ? "block" : "none" }}>
            <Suspense fallback={<TabFallback />}>
              <div className="glass" style={{ padding: 28 }}>
                <FailurePropagation vehicleId={vid} />
              </div>
            </Suspense>
          </div>
        )}

      </div>
    </div>
  );
}

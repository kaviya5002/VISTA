import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";
import { useFleetSocket } from "../hooks/useFleetSocket";
import { useAutoRefresh } from "../hooks/useAutoRefresh";
import { CACHE_TTL } from "../store/fleetStore";

export default function Alerts() {
  const { connected } = useFleetSocket();
  const { data: alertsRaw, loading } = useAutoRefresh<any[]>("alerts", "/alerts", CACHE_TTL.alerts);
  const alerts = alertsRaw ?? [];

  const critical = alerts.filter(a => a.severity === "Critical").length;
  const high     = alerts.filter(a => a.severity === "High").length;

  return (
    <div style={{ background: "#05070A", minHeight: "100vh", paddingTop: 56 }}>
      <Navbar connected={connected} />
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px" }}>

        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>🚨 Alert Center</h1>
          <p style={{ color: "#64748B", fontSize: 14 }}>Live threshold-triggered alerts from all 100 vehicles</p>
        </div>

        {/* Summary pills */}
        <div style={{ display: "flex", gap: 12, marginBottom: 32, flexWrap: "wrap" }}>
          {[
            { label: "Total",    val: alerts.length, color: "#38BDF8" },
            { label: "Critical", val: critical,      color: "#F87171" },
            { label: "High",     val: high,          color: "#FBBF24" },
          ].map(s => (
            <div key={s.label} style={{
              padding: "10px 20px", borderRadius: 12,
              background: s.color + "10",
              border: `1px solid ${s.color}33`,
              color: s.color, fontWeight: 700, fontSize: 20,
              display: "flex", flexDirection: "column", alignItems: "center", minWidth: 100,
            }}>
              <span>{s.val}</span>
              <span style={{ fontSize: 11, fontWeight: 400, color: "#64748B" }}>{s.label}</span>
            </div>
          ))}
        </div>

        {loading ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))", gap: 16 }}>
            {[...Array(6)].map((_, i) => (
              <div key={i} style={{
                height: 130, borderRadius: 14,
                background: "linear-gradient(90deg,rgba(255,255,255,0.03) 25%,rgba(255,255,255,0.07) 50%,rgba(255,255,255,0.03) 75%)",
                backgroundSize: "400px 100%",
                animation: "shimmer 1.4s infinite",
              }} />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div style={{
            padding: 40, textAlign: "center",
            background: "rgba(52,211,153,0.05)",
            border: "1px solid rgba(52,211,153,0.2)",
            borderRadius: 16, color: "#34D399",
          }}>
            ✅ No active alerts — all vehicles nominal
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))", gap: 16 }}>
            {alerts.map((a: any, i: number) => {
              const isCrit = a.severity === "Critical";
              const color  = isCrit ? "#F87171" : "#FBBF24";
              return (
                <Link key={i} to={`/vehicle/${a.vehicle_id}`} style={{ textDecoration: "none" }}>
                  <div style={{
                    padding: "18px 20px", borderRadius: 14,
                    background: color + "08",
                    border: `1px solid ${color}33`,
                    transition: "all 0.2s",
                    animation: isCrit ? "alertPulse 2s infinite" : "none",
                  }}
                    onMouseEnter={e => {
                      (e.currentTarget as HTMLDivElement).style.transform = "translateY(-3px)";
                      (e.currentTarget as HTMLDivElement).style.boxShadow = `0 8px 24px ${color}22`;
                    }}
                    onMouseLeave={e => {
                      (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
                      (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                      <span style={{ fontWeight: 700, fontSize: 15, color }}>{a.alert_type}</span>
                      <span style={{ fontSize: 11, padding: "3px 10px", borderRadius: 12,
                        background: color + "18", color, border: `1px solid ${color}44` }}>
                        {a.severity}
                      </span>
                    </div>
                    <p style={{ fontSize: 13, color: "#94A3B8", marginBottom: 8 }}>
                      🚗 Vehicle {a.vehicle_id}
                    </p>
                    <p style={{ fontSize: 13, color: "#CBD5E1", marginBottom: 10 }}>{a.message}</p>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: 12, color: "#38BDF8" }}>→ {a.action}</span>
                      <span style={{ fontSize: 11, color: "#475569" }}>View Twin →</span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
      <style>{`
        @keyframes alertPulse {
          0%,100% { border-color: rgba(248,113,113,0.3); }
          50%      { border-color: rgba(248,113,113,0.65); }
        }
        @keyframes shimmer {
          0%   { background-position: -400px 0; }
          100% { background-position:  400px 0; }
        }
      `}</style>
    </div>
  );
}

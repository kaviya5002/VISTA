import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../services/api";
import Navbar from "../components/Navbar";
import { useFleetSocket } from "../hooks/useFleetSocket";
import { healthColor } from "../hooks/useCounter";

const SCENARIO_ICONS: Record<string, string> = {
  "Battery Replacement": "🔋",
  "Cooling Repair":      "❄️",
  "Full Service":        "🔧",
  "Ignore Vehicle":      "⏭️",
};

export default function ScenarioSimulator() {
  const { connected } = useFleetSocket();
  const [searchParams]   = useSearchParams();
  const [vehicleId, setVehicleId] = useState(searchParams.get("vehicle_id") ?? "");
  const [result,   setResult]     = useState<any>(null);
  const [loading,  setLoading]    = useState(false);
  const [error,    setError]      = useState("");

  useEffect(() => {
    const id = searchParams.get("vehicle_id");
    if (id) { setVehicleId(id); }
  }, [searchParams]);

  async function run() {
    const id = parseInt(vehicleId);
    if (!id) { setError("Enter a valid vehicle ID"); return; }
    setLoading(true); setError(""); setResult(null);
    try {
      const res = await api.post("/simulate/compare", { vehicle_id: id });
      setResult(res.data);
    } catch {
      setError("Vehicle not found or backend offline.");
    } finally {
      setLoading(false);
    }
  }

  const scenarios: any[] = result ? Object.values(result.comparison) : [];
  const best: string     = result?.best_option ?? "";

  return (
    <div style={{ background: "#05070A", minHeight: "100vh", paddingTop: 56 }}>
      <Navbar connected={connected} />
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px" }}>

        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 4 }}>🔮 AI Scenario Simulator</h1>
        <p style={{ color: "#64748B", marginBottom: 32 }}>What-If Analysis — compare 4 repair options side by side</p>

        {/* Input */}
        <div style={{ display: "flex", gap: 12, marginBottom: 32, alignItems: "center" }}>
          <input
            type="number"
            placeholder="Vehicle ID (1–100)"
            value={vehicleId}
            onChange={e => setVehicleId(e.target.value)}
            onKeyDown={e => e.key === "Enter" && run()}
            style={{
              padding: "10px 16px", borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.1)",
              background: "rgba(255,255,255,0.04)",
              color: "#F1F5F9", fontSize: 14, width: 200,
              outline: "none",
            }}
          />
          <button
            onClick={run}
            disabled={loading}
            style={{
              padding: "10px 24px", borderRadius: 10,
              background: loading ? "rgba(99,102,241,0.4)" : "linear-gradient(135deg,#6366F1,#38BDF8)",
              color: "#fff", fontWeight: 700, fontSize: 14,
              border: "none", transition: "opacity 0.2s",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "Simulating…" : "Run AI Simulation"}
          </button>
        </div>

        {error && (
          <div style={{ color: "#F87171", marginBottom: 20, fontSize: 13 }}>{error}</div>
        )}

        {result && (
          <>
            {/* Best option banner */}
            <div style={{
              padding: "16px 24px", borderRadius: 14, marginBottom: 28,
              background: "rgba(52,211,153,0.06)",
              border: "1px solid rgba(52,211,153,0.25)",
              display: "flex", alignItems: "center", gap: 16,
            }}>
              <span style={{ fontSize: 24 }}>⭐</span>
              <div>
                <div style={{ fontWeight: 700, color: "#34D399", fontSize: 16 }}>Best Option: {best}</div>
                <div style={{ color: "#64748B", fontSize: 13, marginTop: 2 }}>{result.reason}</div>
              </div>
            </div>

            {/* Scenario cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
              {scenarios.map((s: any) => {
                const isBest  = s.scenario === best;
                const hColor  = healthColor(s.health);
                const icon    = SCENARIO_ICONS[s.scenario] ?? "🔧";
                const healthDiff = s.health - (result?.before_health ?? s.health);
                return (
                  <div key={s.scenario} style={{
                    padding: "20px", borderRadius: 16,
                    background: isBest ? "rgba(52,211,153,0.06)" : "rgba(255,255,255,0.03)",
                    border: `1px solid ${isBest ? "rgba(52,211,153,0.35)" : "rgba(255,255,255,0.07)"}`,
                    boxShadow: isBest ? "0 0 24px rgba(52,211,153,0.1)" : "none",
                    transition: "transform 0.2s",
                  }}
                    onMouseEnter={e => (e.currentTarget.style.transform = "translateY(-4px)")}
                    onMouseLeave={e => (e.currentTarget.style.transform = "translateY(0)")}
                  >
                    <div style={{ fontSize: 28, marginBottom: 10 }}>{icon}</div>
                    <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14, color: isBest ? "#34D399" : "#F1F5F9" }}>
                      {isBest && "⭐ "}{s.scenario}
                    </div>

                    {/* Health */}
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                        <span style={{ fontSize: 12, color: "#64748B" }}>Health</span>
                        <span style={{ fontSize: 14, fontWeight: 700, color: hColor }}>{s.health}%</span>
                      </div>
                      <div style={{ height: 6, background: "rgba(255,255,255,0.06)", borderRadius: 4 }}>
                        <div style={{ width: `${s.health}%`, height: "100%", background: hColor, borderRadius: 4, transition: "width 1s" }} />
                      </div>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13 }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "#64748B" }}>Failure Risk</span>
                        <span style={{ color: s.failure_probability > 60 ? "#F87171" : "#FBBF24", fontWeight: 600 }}>
                          {s.failure_probability}%
                        </span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "#64748B" }}>RUL</span>
                        <span style={{ color: "#38BDF8", fontWeight: 600 }}>{s.rul_days}d</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "#64748B" }}>Repair Cost</span>
                        <span style={{ color: "#F1F5F9" }}>₹{s.repair_cost.toLocaleString("en-IN")}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "#64748B" }}>Savings</span>
                        <span style={{ color: "#34D399", fontWeight: 700 }}>₹{s.potential_savings.toLocaleString("en-IN")}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span style={{ color: "#64748B" }}>AI Score</span>
                        <span style={{ color: "#A78BFA", fontWeight: 700 }}>{s.ai_score}</span>
                      </div>
                    </div>

                    <div style={{
                      marginTop: 14, padding: "8px 12px", borderRadius: 8,
                      background: "rgba(255,255,255,0.04)",
                      fontSize: 12, color: "#64748B", lineHeight: 1.4,
                    }}>
                      {s.recommendation}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

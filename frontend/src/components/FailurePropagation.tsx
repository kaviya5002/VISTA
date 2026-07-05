import { useEffect, useRef, useState } from "react";
import api from "../services/api";

interface XAIFactor { name: string; value: string; impact: number; }
interface PropNode {
  id: string; label: string; icon: string; category: string;
  probability: number; day: number; confidence: number;
  severity: "healthy" | "warning" | "high" | "critical";
  xai_factors: XAIFactor[];
}
interface PropData {
  chain_name: string; overall_risk: string; terminal_probability: number;
  rul: number; nodes: PropNode[]; reasoning: string[];
  health_score: number; failure_probability: number;
}

const SEV_COLOR: Record<string, string> = {
  healthy:  "#34D399",
  warning:  "#FBBF24",
  high:     "#FB923C",
  critical: "#F87171",
};

const CAT_COLOR: Record<string, string> = {
  electrical:   "#38BDF8",
  cooling:      "#67E8F9",
  motor:        "#F87171",
  mechanical:   "#FB923C",
  brakes:       "#FBBF24",
  transmission: "#A78BFA",
  sensors:      "#94A3B8",
  safety:       "#F87171",
  terminal:     "#F87171",
  general:      "#64748B",
};

export default function FailurePropagation({ vehicleId }: { vehicleId: number }) {
  const [data,        setData]        = useState<PropData | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [activeNode,  setActiveNode]  = useState<PropNode | null>(null);
  const [animated,    setAnimated]    = useState<Set<number>>(new Set());
  const [flowActive,  setFlowActive]  = useState(false);
  const animRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    setLoading(true);
    setAnimated(new Set());
    setFlowActive(false);
    setActiveNode(null);
    animRef.current.forEach(clearTimeout);
    animRef.current = [];

    api.get(`/vehicle/${vehicleId}/propagation`)
      .then(r => {
        setData(r.data);
        setLoading(false);
        // Stagger node animations
        r.data.nodes.forEach((_: PropNode, i: number) => {
          const t = setTimeout(() => {
            setAnimated(prev => new Set([...prev, i]));
            if (i === r.data.nodes.length - 1) setFlowActive(true);
          }, 300 + i * 420);
          animRef.current.push(t);
        });
      })
      .catch(() => setLoading(false));

    return () => animRef.current.forEach(clearTimeout);
  }, [vehicleId]);

  if (loading) return <PropLoading />;
  if (!data)   return <div style={{ color: "#64748B", padding: 40, textAlign: "center" }}>Failed to load propagation data.</div>;

  const riskColor = SEV_COLOR[data.overall_risk.toLowerCase()] ?? "#FBBF24";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>

      {/* ── Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 6 }}>
            ⚡ AI Failure Propagation Engine
          </h2>
          <p style={{ fontSize: 12, color: "#64748B" }}>
            Knowledge graph path selected by Root Cause ML · Probabilities weighted by live sensor data
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Pill label={`Chain: ${data.chain_name}`}         color="#A78BFA" />
          <Pill label={`Risk: ${data.overall_risk}`}        color={riskColor} />
          <Pill label={`Terminal: ${Math.round(data.terminal_probability * 100)}%`} color={riskColor} />
          <Pill label={`RUL: ${data.rul}d`}                 color={data.rul <= 7 ? "#F87171" : "#34D399"} />
        </div>
      </div>

      {/* ── Main layout: chain + XAI panel ── */}
      <div style={{ display: "grid", gridTemplateColumns: activeNode ? "1fr 300px" : "1fr", gap: 20, transition: "all 0.3s" }}>

        {/* ── Propagation Chain ── */}
        <div className="glass" style={{ padding: 28 }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0 }}>
            {data.nodes.map((node, i) => {
              const color   = SEV_COLOR[node.severity];
              const catCol  = CAT_COLOR[node.category] ?? "#64748B";
              const visible = animated.has(i);
              const isLast  = i === data.nodes.length - 1;
              const isActive = activeNode?.id === node.id;

              return (
                <div key={node.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>

                  {/* Node card */}
                  <div
                    onClick={() => setActiveNode(isActive ? null : node)}
                    style={{
                      width: "min(480px, 100%)",
                      padding: "14px 20px",
                      borderRadius: 14,
                      background: isActive
                        ? `${color}18`
                        : visible ? `${color}0C` : "rgba(255,255,255,0.02)",
                      border: `1px solid ${isActive ? color : visible ? color + "55" : "rgba(255,255,255,0.06)"}`,
                      cursor: "pointer",
                      transition: "all 0.4s ease",
                      opacity: visible ? 1 : 0,
                      transform: visible ? "translateY(0) scale(1)" : "translateY(20px) scale(0.96)",
                      boxShadow: isActive ? `0 0 20px ${color}33` : visible && node.severity === "critical" ? `0 0 12px ${color}22` : "none",
                      animation: visible && node.severity === "critical" && flowActive
                        ? "nodePulse 2.5s ease-in-out infinite" : "none",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      {/* Icon with glow */}
                      <div style={{
                        width: 40, height: 40, borderRadius: 10,
                        background: `${color}18`, border: `1px solid ${color}44`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 18, flexShrink: 0,
                        boxShadow: visible ? `0 0 10px ${color}33` : "none",
                      }}>
                        {node.icon}
                      </div>

                      {/* Label + category */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: "#F1F5F9", marginBottom: 2 }}>
                          {node.label}
                        </div>
                        <div style={{ fontSize: 11, color: catCol, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                          {node.category}
                        </div>
                      </div>

                      {/* Probability + day */}
                      <div style={{ textAlign: "right", flexShrink: 0 }}>
                        <div style={{ fontSize: 18, fontWeight: 900, color, lineHeight: 1 }}>
                          {Math.round(node.probability * 100)}%
                        </div>
                        <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>
                          Day {node.day}
                        </div>
                      </div>

                      {/* Confidence badge */}
                      <div style={{
                        padding: "3px 8px", borderRadius: 8,
                        background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.25)",
                        fontSize: 11, color: "#A78BFA", flexShrink: 0,
                      }}>
                        {node.confidence}%
                      </div>
                    </div>

                    {/* Probability bar */}
                    <div style={{ marginTop: 10, height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 3 }}>
                      <div style={{
                        width: visible ? `${node.probability * 100}%` : "0%",
                        height: "100%", background: color, borderRadius: 3,
                        transition: "width 0.8s ease 0.2s",
                        boxShadow: `0 0 6px ${color}`,
                      }} />
                    </div>

                    {isActive && (
                      <div style={{ marginTop: 8, fontSize: 11, color: "#64748B" }}>
                        Click again to close · See XAI panel →
                      </div>
                    )}
                  </div>

                  {/* Animated connector arrow */}
                  {!isLast && (
                    <div style={{
                      display: "flex", flexDirection: "column", alignItems: "center",
                      height: 36, gap: 0,
                      opacity: animated.has(i + 1) ? 1 : 0.15,
                      transition: "opacity 0.4s ease",
                    }}>
                      <div style={{
                        width: 2, flex: 1,
                        background: `linear-gradient(to bottom, ${color}, ${SEV_COLOR[data.nodes[i + 1]?.severity] ?? color})`,
                        opacity: 0.5,
                      }} />
                      <div style={{
                        fontSize: 14,
                        color: SEV_COLOR[data.nodes[i + 1]?.severity] ?? color,
                        lineHeight: 1,
                        animation: flowActive ? "arrowBounce 1.5s ease-in-out infinite" : "none",
                      }}>▼</div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── XAI Side Panel ── */}
        {activeNode && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="glass" style={{ padding: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: SEV_COLOR[activeNode.severity] }}>
                  {activeNode.icon} {activeNode.label}
                </h3>
                <button
                  onClick={() => setActiveNode(null)}
                  style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: 16 }}
                >✕</button>
              </div>

              {/* Stats */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
                {[
                  { label: "Probability", val: `${Math.round(activeNode.probability * 100)}%`, color: SEV_COLOR[activeNode.severity] },
                  { label: "Day",         val: `Day ${activeNode.day}`,                        color: "#38BDF8" },
                  { label: "Confidence",  val: `${activeNode.confidence}%`,                    color: "#A78BFA" },
                  { label: "Severity",    val: activeNode.severity,                             color: SEV_COLOR[activeNode.severity] },
                ].map(s => (
                  <div key={s.label} style={{
                    padding: "10px 12px", borderRadius: 10,
                    background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                  }}>
                    <div style={{ fontSize: 10, color: "#475569", marginBottom: 4 }}>{s.label}</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: s.color }}>{s.val}</div>
                  </div>
                ))}
              </div>

              {/* XAI factors */}
              <div style={{ marginBottom: 4 }}>
                <div style={{ fontSize: 11, color: "#64748B", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Why this node?
                </div>
                {activeNode.xai_factors.map((f, i) => (
                  <div key={i} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
                      <span style={{ color: "#94A3B8" }}>{f.name}</span>
                      <span style={{ color: "#F1F5F9", fontWeight: 600 }}>{f.value} <span style={{ color: "#F87171" }}>+{f.impact}%</span></span>
                    </div>
                    <div style={{ height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 3 }}>
                      <div style={{
                        width: `${Math.min(f.impact * 2.5, 100)}%`, height: "100%",
                        background: `linear-gradient(90deg, #38BDF8, #A78BFA)`, borderRadius: 3,
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Component health hint */}
            <div className="glass" style={{ padding: 16 }}>
              <div style={{ fontSize: 11, color: "#64748B", marginBottom: 8 }}>Recommended Action</div>
              <div style={{ fontSize: 13, color: "#F1F5F9", lineHeight: 1.6 }}>
                {activeNode.severity === "critical"
                  ? "⚠️ Immediate inspection required. Schedule workshop visit within 24 hours."
                  : activeNode.severity === "high"
                  ? "🔧 Schedule maintenance within 3–5 days to prevent escalation."
                  : activeNode.severity === "warning"
                  ? "📋 Monitor closely. Plan service within 2 weeks."
                  : "✅ Within acceptable range. Continue routine monitoring."}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── AI Reasoning ── */}
      <div className="glass" style={{ padding: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#A78BFA", marginBottom: 12 }}>
          🧠 Why this propagation path?
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 8 }}>
          {data.reasoning.map((r, i) => (
            <div key={i} style={{
              fontSize: 12, color: "#94A3B8", lineHeight: 1.6,
              padding: "8px 12px", borderRadius: 8,
              background: "rgba(255,255,255,0.02)",
              borderLeft: "2px solid rgba(167,139,250,0.3)",
            }}>
              {r}
            </div>
          ))}
        </div>
      </div>

      {/* ── Timeline bar ── */}
      <div className="glass" style={{ padding: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#38BDF8", marginBottom: 16 }}>
          📅 Failure Timeline (RUL: {data.rul} days)
        </div>
        <div style={{ position: "relative", height: 60 }}>
          {/* Track */}
          <div style={{
            position: "absolute", top: 28, left: 0, right: 0, height: 2,
            background: "rgba(255,255,255,0.06)", borderRadius: 2,
          }} />
          {/* Progress fill */}
          <div style={{
            position: "absolute", top: 28, left: 0, height: 2,
            width: flowActive ? "100%" : "0%",
            background: `linear-gradient(90deg, #34D399, #FBBF24, #F87171)`,
            borderRadius: 2, transition: "width 2s ease 0.5s",
          }} />
          {/* Node markers */}
          {data.nodes.map((node, i) => {
            const pct   = data.rul > 0 ? (node.day / data.rul) * 100 : i * (100 / data.nodes.length);
            const color = SEV_COLOR[node.severity];
            return (
              <div
                key={node.id}
                onClick={() => setActiveNode(activeNode?.id === node.id ? null : node)}
                style={{
                  position: "absolute",
                  left: `${Math.min(pct, 96)}%`,
                  top: 20,
                  transform: "translateX(-50%)",
                  cursor: "pointer",
                  opacity: animated.has(i) ? 1 : 0,
                  transition: "opacity 0.4s ease",
                }}
              >
                <div style={{
                  width: 16, height: 16, borderRadius: "50%",
                  background: color, border: "2px solid #05070A",
                  boxShadow: `0 0 8px ${color}`,
                  margin: "0 auto",
                }} />
                <div style={{
                  fontSize: 9, color, textAlign: "center", marginTop: 4,
                  whiteSpace: "nowrap", maxWidth: 60,
                  overflow: "hidden", textOverflow: "ellipsis",
                }}>
                  {node.icon} d{node.day}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <style>{`
        @keyframes nodePulse {
          0%,100% { box-shadow: 0 0 12px rgba(248,113,113,0.2); }
          50%      { box-shadow: 0 0 24px rgba(248,113,113,0.5); }
        }
        @keyframes arrowBounce {
          0%,100% { transform: translateY(0); }
          50%      { transform: translateY(3px); }
        }
      `}</style>
    </div>
  );
}

function Pill({ label, color }: { label: string; color: string }) {
  return (
    <div style={{
      padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 600,
      background: color + "14", border: `1px solid ${color}44`, color,
    }}>{label}</div>
  );
}

function PropLoading() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "8px 0" }}>
      <div style={{ display: "flex", gap: 10, marginBottom: 8 }}>
        {[120, 100, 140, 80].map((w, i) => (
          <div key={i} style={{ height: 28, width: w, borderRadius: 20, background: "rgba(255,255,255,0.05)", animation: "shimmer 1.4s infinite" }} />
        ))}
      </div>
      {[...Array(5)].map((_, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ width: "min(480px,100%)", height: 72, borderRadius: 14, background: "rgba(255,255,255,0.04)", animation: "shimmer 1.4s infinite" }} />
          {i < 4 && <div style={{ width: 2, height: 36, background: "rgba(255,255,255,0.04)", margin: "2px 0" }} />}
        </div>
      ))}
      <style>{`@keyframes shimmer { 0%{opacity:0.5} 50%{opacity:1} 100%{opacity:0.5} }`}</style>
    </div>
  );
}

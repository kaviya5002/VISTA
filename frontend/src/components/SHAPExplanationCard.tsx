import { useEffect, useState } from "react";
import api from "../services/api";

interface Factor {
  rank: number;
  label: string;
  impact: number;
  direction: string;
  shap_value: number;
}

interface SHAPData {
  failure_probability: number;
  health_score: number;
  rul_days: number;
  status: string;
  confidence: number;
  top_factors: Factor[];
  explanation: string;
  factors_text: string[];
  rul_note: string;
  recommendation: string;
  confidence_note: string;
  shap_enabled: boolean;
}

const STATUS_COLOR: Record<string, string> = {
  Healthy:  "#34D399",
  Warning:  "#FBBF24",
  Critical: "#F87171",
};

const BAR_COLOR = (direction: string) =>
  direction === "increases_risk" ? "#F87171" : "#34D399";

export default function SHAPExplanationCard({ vehicleId }: { vehicleId: number }) {
  const [data,    setData]    = useState<SHAPData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showWhy, setShowWhy] = useState(false);
  const [animate, setAnimate] = useState(false);

  useEffect(() => {
    setLoading(true);
    setAnimate(false);
    api.get(`/xai/shap/${vehicleId}`)
      .then(r => {
        setData(r.data);
        setLoading(false);
        setTimeout(() => setAnimate(true), 100);
      })
      .catch(() => setLoading(false));
  }, [vehicleId]);

  if (loading) return (
    <div className="glass" style={{ padding: 24, textAlign: "center", color: "#475569" }}>
      Loading AI Explanation…
    </div>
  );

  if (!data) return null;

  const sc = STATUS_COLOR[data.status] ?? "#94A3B8";

  return (
    <div className="glass" style={{ padding: 24 }}>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 16, marginBottom: 4 }}>
            🧠 AI Explanation
            {data.shap_enabled && (
              <span style={{
                marginLeft: 8, fontSize: 10, padding: "2px 8px", borderRadius: 10,
                background: "rgba(56,189,248,0.15)", color: "#38BDF8",
                fontWeight: 600, letterSpacing: "0.5px",
              }}>SHAP</span>
            )}
          </h2>
          <p style={{ fontSize: 12, color: "#64748B" }}>
            Per-vehicle contribution analysis
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 28, fontWeight: 900, color: sc }}>
            {data.failure_probability}%
          </div>
          <div style={{ fontSize: 11, color: "#64748B" }}>Failure Risk</div>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        {[
          { label: "Health",     val: `${data.health_score}%`,  color: data.health_score >= 70 ? "#34D399" : data.health_score >= 50 ? "#FBBF24" : "#F87171" },
          { label: "RUL",        val: `${data.rul_days}d`,      color: data.rul_days <= 7 ? "#F87171" : "#38BDF8" },
          { label: "Confidence", val: `${data.confidence}%`,    color: "#A78BFA" },
          { label: "Status",     val: data.status,              color: sc },
        ].map(s => (
          <div key={s.label} style={{
            flex: 1, padding: "10px 12px", borderRadius: 10,
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.07)",
            textAlign: "center",
          }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: s.color }}>{s.val}</div>
            <div style={{ fontSize: 10, color: "#64748B", marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Top Contributors */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#94A3B8", marginBottom: 12 }}>
          Top Contributors
        </div>
        {data.top_factors.map(f => (
          <div key={f.rank} style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
              <span style={{ color: "#E2E8F0" }}>{f.label}</span>
              <span style={{
                color: BAR_COLOR(f.direction),
                fontWeight: 700,
              }}>
                {f.direction === "increases_risk" ? "+" : "-"}{f.impact}%
              </span>
            </div>
            {/* Animated bar */}
            <div style={{ height: 6, background: "rgba(255,255,255,0.06)", borderRadius: 4, overflow: "hidden" }}>
              <div style={{
                height: "100%",
                width: animate ? `${f.impact}%` : "0%",
                background: `linear-gradient(90deg, ${BAR_COLOR(f.direction)}99, ${BAR_COLOR(f.direction)})`,
                borderRadius: 4,
                transition: `width ${0.4 + f.rank * 0.1}s ease`,
                boxShadow: `0 0 8px ${BAR_COLOR(f.direction)}66`,
              }} />
            </div>
          </div>
        ))}
      </div>

      {/* Why button */}
      <button
        onClick={() => setShowWhy(v => !v)}
        style={{
          width: "100%", padding: "10px 16px", borderRadius: 10,
          background: showWhy ? "rgba(56,189,248,0.15)" : "rgba(56,189,248,0.08)",
          border: "1px solid rgba(56,189,248,0.3)",
          color: "#38BDF8", fontWeight: 600, fontSize: 13,
          cursor: "pointer", transition: "all 0.2s",
          marginBottom: showWhy ? 16 : 0,
        }}
      >
        {showWhy ? "▲ Hide Explanation" : "💡 Why is this vehicle at risk?"}
      </button>

      {/* Explanation panel */}
      {showWhy && (
        <div style={{
          padding: 16, borderRadius: 10,
          background: "rgba(56,189,248,0.05)",
          border: "1px solid rgba(56,189,248,0.15)",
          animation: "fadeIn 0.3s ease",
        }}>
          {/* Summary */}
          <p style={{ fontSize: 13, color: "#CBD5E1", marginBottom: 12, lineHeight: 1.6 }}>
            {data.explanation}
          </p>

          {/* Factor sentences */}
          <div style={{ marginBottom: 12 }}>
            {data.factors_text.map((t, i) => (
              <div key={i} style={{
                fontSize: 12, color: "#94A3B8", padding: "4px 0",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                lineHeight: 1.5,
              }}>
                • {t}
              </div>
            ))}
          </div>

          {/* RUL note */}
          <div style={{
            padding: "8px 12px", borderRadius: 8, marginBottom: 10,
            background: "rgba(251,191,36,0.08)",
            border: "1px solid rgba(251,191,36,0.2)",
            fontSize: 12, color: "#FBBF24",
          }}>
            ⏱ {data.rul_note}
          </div>

          {/* Recommendation */}
          <div style={{
            padding: "10px 14px", borderRadius: 8,
            background: "rgba(167,139,250,0.08)",
            border: "1px solid rgba(167,139,250,0.25)",
            fontSize: 13, color: "#A78BFA", fontWeight: 600,
          }}>
            → {data.recommendation}
          </div>

          {/* Confidence note */}
          <p style={{ fontSize: 10, color: "#475569", marginTop: 10, lineHeight: 1.5 }}>
            {data.confidence_note}
          </p>
        </div>
      )}

      <style>{`
        @keyframes fadeIn { from { opacity:0; transform:translateY(-6px); } to { opacity:1; transform:translateY(0); } }
      `}</style>
    </div>
  );
}

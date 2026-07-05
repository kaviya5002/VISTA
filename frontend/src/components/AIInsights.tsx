import { useEffect, useState } from "react";

interface Props {
  vehicles: any[];
  critical: number;
  avgHealth: number;
  totalSavings: number;
}

export default function AIInsights({ vehicles, critical, avgHealth, totalSavings }: Props) {
  const [visible, setVisible] = useState(0);

  // Battery degradation count
  const battDeg = vehicles.filter(v =>
    v.root_cause?.some((c: string) => c.toLowerCase().includes("battery"))
  ).length;
  const highTemp = vehicles.filter(v => v.temperature > 90).length;
  const highRisk = vehicles.filter(v => v.failure_probability > 70).length;
  const shortRul = vehicles.filter(v => v.remaining_useful_life_days <= 7).length;

  const insights = [
    { icon: "🔋", color: "#FBBF24", conf: 98,
      text: `Battery degradation detected on ${battDeg} vehicles — immediate voltage checks recommended` },
    { icon: "🌡️", color: "#F87171", conf: 94,
      text: `${highTemp} vehicles running above 90°C — cooling system stress detected` },
    { icon: "⚠️", color: "#F87171", conf: 97,
      text: `${highRisk} vehicles at high failure probability — schedule urgent maintenance` },
    { icon: "📅", color: "#38BDF8", conf: 91,
      text: `${shortRul} vehicles have RUL ≤ 7 days — service window closing fast` },
    { icon: "💰", color: "#34D399", conf: 96,
      text: `Preventive maintenance now saves ₹${totalSavings.toLocaleString("en-IN")} in failure costs` },
    { icon: "🏥", color: avgHealth < 60 ? "#F87171" : "#34D399", conf: 89,
      text: `Fleet average health ${avgHealth}% — ${avgHealth < 60 ? "below optimal threshold" : "within acceptable range"}` },
  ];

  useEffect(() => {
    if (!vehicles.length) return;
    setVisible(0);
    insights.forEach((_, i) => {
      setTimeout(() => setVisible(i + 1), i * 180);
    });
  }, [vehicles.length]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {insights.map((ins, i) => (
        <div key={i} style={{
          display: "flex", gap: 12, alignItems: "flex-start",
          padding: "12px 16px",
          background: "rgba(255,255,255,0.03)",
          border: `1px solid ${ins.color}22`,
          borderLeft: `3px solid ${ins.color}`,
          borderRadius: 10,
          opacity: i < visible ? 1 : 0,
          transform: i < visible ? "translateX(0)" : "translateX(-12px)",
          transition: "all 0.4s ease",
        }}>
          <span style={{ fontSize: 18, flexShrink: 0 }}>{ins.icon}</span>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: 13, color: "#CBD5E1", lineHeight: 1.5 }}>{ins.text}</p>
          </div>
          <div style={{ flexShrink: 0, textAlign: "right" }}>
            <div style={{ fontSize: 11, color: "#64748B" }}>Confidence</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: ins.color }}>{ins.conf}%</div>
          </div>
        </div>
      ))}
    </div>
  );
}

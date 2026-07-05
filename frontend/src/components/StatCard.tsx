import { useCounter } from "../hooks/useCounter";

interface Props {
  label: string;
  value: number;
  suffix?: string;
  prefix?: string;
  color?: string;
  sub?: string;
}

export default function StatCard({ label, value, suffix = "", prefix = "", color = "#38BDF8", sub }: Props) {
  const animated = useCounter(value, 1400);
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: 14,
      padding: "18px 22px",
      display: "flex", flexDirection: "column", gap: 4,
      transition: "transform 0.2s, box-shadow 0.2s",
      cursor: "default",
    }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = `0 8px 24px ${color}22`;
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
      }}
    >
      <span style={{ fontSize: 11, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.8px" }}>{label}</span>
      <span style={{ fontSize: 28, fontWeight: 800, color, lineHeight: 1, letterSpacing: "-1px" }}>
        {prefix}{animated.toLocaleString()}{suffix}
      </span>
      {sub && <span style={{ fontSize: 11, color: "#475569" }}>{sub}</span>}
    </div>
  );
}

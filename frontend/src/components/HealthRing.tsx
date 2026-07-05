import { useEffect, useState } from "react";
import { healthColor } from "../hooks/useCounter";

export default function HealthRing({ value, size = 160 }: { value: number; size?: number }) {
  const [anim, setAnim] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setAnim(value), 100);
    return () => clearTimeout(t);
  }, [value]);

  const R = size / 2 - 14;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * R;
  const dash = (anim / 100) * circ;
  const color = healthColor(value);

  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        {/* track */}
        <circle cx={cx} cy={cy} r={R} fill="none"
          stroke="rgba(255,255,255,0.06)" strokeWidth={10} />
        {/* progress */}
        <circle cx={cx} cy={cy} r={R} fill="none"
          stroke={color} strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: "stroke-dasharray 1.2s cubic-bezier(0.34,1.56,0.64,1), stroke 0.6s" }}
          filter={`drop-shadow(0 0 8px ${color})`}
        />
      </svg>
      <div style={{
        position: "absolute", inset: 0,
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
      }}>
        <span style={{ fontSize: size * 0.22, fontWeight: 800, color, lineHeight: 1 }}>{anim}%</span>
        <span style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>Fleet Health</span>
      </div>
    </div>
  );
}

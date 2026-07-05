/**
 * DigitalHUDOverlay — screen-space 2D holographic HUD overlay
 * rendered inside the Canvas via Html portal (fixed position).
 *
 * Shows:
 *  • Corner bracket decorations
 *  • Vehicle health ring arc
 *  • Live sensor readouts (Voltage, Temp, RPM, Failure%, RUL, Confidence)
 *  • Animated scan-line sweep across the HUD
 *  • Status text
 */
import { Html } from "@react-three/drei";
import type { TwinData } from "./useTwinAnimation";

interface Props {
  twinData:          TwinData;
  hoveredComponent:  string | null;
  selectedComponent: string | null;
}

function HealthArc({ health }: { health: number }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dash = (health / 100) * circ;
  const color = health >= 75 ? "#00ffcc" : health >= 45 ? "#f59e0b" : "#ef4444";
  return (
    <svg width={72} height={72} style={{ display: "block" }}>
      <circle cx={36} cy={36} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={3} />
      <circle
        cx={36} cy={36} r={r}
        fill="none"
        stroke={color}
        strokeWidth={3}
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 36 36)"
        style={{ filter: `drop-shadow(0 0 4px ${color})`, transition: "stroke-dasharray 0.8s ease" }}
      />
      <text x={36} y={40} textAnchor="middle" fill={color} fontSize={13} fontWeight={900} fontFamily="monospace">
        {health}%
      </text>
    </svg>
  );
}

function Corner({ pos }: { pos: "tl" | "tr" | "bl" | "br" }) {
  const size = 14;
  const color = "#00CFFF";
  const style: React.CSSProperties = {
    position: "absolute",
    width: size, height: size,
    borderColor: color,
    borderStyle: "solid",
    borderWidth: 0,
    opacity: 0.7,
  };
  const corners: Record<string, React.CSSProperties> = {
    tl: { top: 0, left: 0,   borderTopWidth: 2, borderLeftWidth: 2,   borderRadius: "4px 0 0 0" },
    tr: { top: 0, right: 0,  borderTopWidth: 2, borderRightWidth: 2,  borderRadius: "0 4px 0 0" },
    bl: { bottom: 0, left: 0,  borderBottomWidth: 2, borderLeftWidth: 2,  borderRadius: "0 0 0 4px" },
    br: { bottom: 0, right: 0, borderBottomWidth: 2, borderRightWidth: 2, borderRadius: "0 0 4px 0" },
  };
  return <div style={{ ...style, ...corners[pos] }} />;
}

function MetricBox({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      display: "flex", flexDirection: "column", alignItems: "center",
      padding: "4px 8px",
      background: "rgba(0,207,255,0.04)",
      border: "1px solid rgba(0,207,255,0.1)",
      borderRadius: 5, minWidth: 52,
    }}>
      <span style={{ fontSize: 13, fontWeight: 900, color, fontFamily: "monospace", lineHeight: 1 }}>{value}</span>
      <span style={{ fontSize: 8, color: "#334155", marginTop: 2, letterSpacing: 0.5 }}>{label}</span>
    </div>
  );
}

export default function DigitalHUDOverlay({ twinData, hoveredComponent, selectedComponent }: Props) {
  const statusColor = twinData.vehicle_status === "Healthy" ? "#00ffcc"
    : twinData.vehicle_status === "Warning" ? "#f59e0b" : "#ef4444";

  const voltage = Number(twinData.battery.sensors?.voltage ?? 12.0).toFixed(1);
  const temp    = Number(twinData.motor.sensors?.temperature ?? 75).toFixed(1);
  const rpm     = Math.round(Number(twinData.motor.sensors?.rpm ?? 2400));
  const fp      = Math.round(twinData.battery.failure_probability * 100);
  const rul     = twinData.battery.rul;
  const conf    = Math.round((twinData.battery.confidence + twinData.motor.confidence + twinData.cooling.confidence) / 3);

  const active = hoveredComponent ?? selectedComponent;

  return (
    <Html
      fullscreen
      zIndexRange={[5, 0]}
      style={{ pointerEvents: "none" }}
    >
      <style>{`
        @keyframes hudScan {
          0%   { top: 0%; opacity: 0; }
          10%  { opacity: 1; }
          90%  { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
        @keyframes hudBlink {
          0%,100% { opacity: 1; }
          50%     { opacity: 0.3; }
        }
        @keyframes hudFadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* ── Top-left corner panel ── */}
      <div style={{
        position: "absolute", top: 16, left: 16,
        background: "rgba(5,7,14,0.82)",
        border: "1px solid rgba(0,207,255,0.15)",
        borderRadius: 8, padding: "10px 14px",
        fontFamily: "monospace",
        animation: "hudFadeIn 0.5s ease forwards",
        backdropFilter: "blur(6px)",
        minWidth: 160,
      }}>
        <Corner pos="tl" /><Corner pos="tr" /><Corner pos="bl" /><Corner pos="br" />

        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <HealthArc health={twinData.vehicle_health} />
          <div>
            <div style={{ fontSize: 10, color: "#475569", letterSpacing: 0.5 }}>VEHICLE STATUS</div>
            <div style={{
              fontSize: 12, fontWeight: 900, color: statusColor, marginTop: 2,
              animation: twinData.vehicle_status === "Critical" ? "hudBlink 1s infinite" : "none",
            }}>
              {twinData.vehicle_status.toUpperCase()}
            </div>
            {twinData.critical_components.length > 0 && (
              <div style={{ fontSize: 9, color: "#ef4444", marginTop: 3 }}>
                ⚠ {twinData.critical_components.slice(0, 2).join(", ")}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          <MetricBox label="VOLTAGE" value={`${voltage}V`} color="#a78bfa" />
          <MetricBox label="TEMP"    value={`${temp}°C`}   color={Number(temp) > 90 ? "#ef4444" : "#f59e0b"} />
          <MetricBox label="RPM"     value={`${rpm}`}      color="#22c55e" />
        </div>
      </div>

      {/* ── Top-right corner panel ── */}
      <div style={{
        position: "absolute", top: 16, right: 16,
        background: "rgba(5,7,14,0.82)",
        border: "1px solid rgba(0,207,255,0.15)",
        borderRadius: 8, padding: "10px 14px",
        fontFamily: "monospace",
        animation: "hudFadeIn 0.5s ease 0.1s forwards",
        backdropFilter: "blur(6px)",
        opacity: 0,
        minWidth: 140,
      }}>
        <Corner pos="tl" /><Corner pos="tr" /><Corner pos="bl" /><Corner pos="br" />

        <div style={{ fontSize: 9, color: "#475569", marginBottom: 8, letterSpacing: 0.8 }}>AI DIAGNOSTICS</div>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          <MetricBox label="FAIL%"  value={`${fp}%`}   color={fp > 60 ? "#ef4444" : fp > 35 ? "#f59e0b" : "#22c55e"} />
          <MetricBox label="RUL"    value={`${rul}d`}  color="#38bdf8" />
          <MetricBox label="CONF"   value={`${conf}%`} color="#00ffcc" />
        </div>

        {active && (
          <div style={{
            marginTop: 8, fontSize: 9, color: "#38bdf8",
            borderTop: "1px solid rgba(56,189,248,0.15)", paddingTop: 6,
            animation: "hudFadeIn 0.2s ease forwards",
          }}>
            ◉ {active.toUpperCase()} SELECTED
          </div>
        )}
      </div>

      {/* ── Scan line sweep across full screen ── */}
      <div style={{
        position: "absolute", left: 0, right: 0, height: 1,
        background: "linear-gradient(90deg, transparent, rgba(0,207,255,0.4), transparent)",
        animation: "hudScan 4s linear infinite",
        pointerEvents: "none",
      }} />

      {/* ── Bottom center status bar ── */}
      <div style={{
        position: "absolute", bottom: 12, left: "50%",
        transform: "translateX(-50%)",
        background: "rgba(5,7,14,0.75)",
        border: "1px solid rgba(0,207,255,0.12)",
        borderRadius: 20, padding: "4px 16px",
        fontFamily: "monospace", fontSize: 10,
        color: "#334155", whiteSpace: "nowrap",
        backdropFilter: "blur(4px)",
      }}>
        <span style={{ color: "#00CFFF", marginRight: 8 }}>⬡</span>
        TWINGUARD HOLOGRAPHIC MONITORING SYSTEM
        <span style={{ color: "#00CFFF", marginLeft: 8 }}>⬡</span>
      </div>
    </Html>
  );
}

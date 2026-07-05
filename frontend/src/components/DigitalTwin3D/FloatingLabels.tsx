/**
 * FloatingLabels — premium holographic component labels
 *
 * Each label:
 *   • Floats up/down with a sine wave (staggered per component)
 *   • Fades in on mount
 *   • Scales up smoothly on hover
 *   • Shows compact view normally, expands on hover with full metrics
 *   • Health bar with glow
 *   • Corner bracket accents
 *
 * Reads positions from ComponentRegistry.labelOffset — nothing hardcoded.
 */
import { Html } from "@react-three/drei";
import * as THREE from "three";
import { REGISTRY } from "./ComponentRegistry";
import type { ComponentState } from "./useTwinAnimation";

interface LabelProps {
  position:  [number, number, number];
  name:      string;
  icon:      string;
  comp:      ComponentState;
  hovered:   boolean;
  color:     THREE.Color;
  onClick:   () => void;
  floatIdx:  number;
}

function Label({ position, name, icon, comp, hovered, color, onClick, floatIdx }: LabelProps) {
  const hex = "#" + color.getHexString();
  const hc  = comp.health >= 75 ? "#00ffcc" : comp.health >= 45 ? "#f59e0b" : "#ef4444";
  const fp  = Math.round(comp.failure_probability * 100);
  const fpC = fp > 60 ? "#ef4444" : fp > 35 ? "#f59e0b" : "#22c55e";

  // Stagger float animation per component index
  const floatDelay = floatIdx * 0.55;
  const floatDur   = 2.8 + floatIdx * 0.3;

  return (
    <Html position={position} center distanceFactor={8} zIndexRange={[10, 0]}>
      <div
        onClick={onClick}
        style={{
          position: "relative",
          background: hovered ? "rgba(5,7,14,0.98)" : "rgba(5,7,14,0.85)",
          border: `1px solid ${hovered ? hex : hex + "55"}`,
          borderRadius: 8,
          padding: hovered ? "10px 14px" : "6px 11px",
          color: "#e2e8f0",
          fontSize: 11,
          whiteSpace: "nowrap",
          cursor: "pointer",
          fontFamily: "monospace",
          minWidth: hovered ? 140 : 96,
          userSelect: "none",
          // Smooth scale + float
          transform: hovered ? "scale(1.08)" : "scale(1)",
          transition: "all 0.22s cubic-bezier(0.4,0,0.2,1)",
          boxShadow: hovered
            ? `0 0 20px ${hex}55, 0 0 8px ${hex}33, inset 0 0 10px ${hex}08`
            : `0 0 8px ${hex}22`,
          animation: `labelFloat${floatIdx} ${floatDur}s ${floatDelay}s ease-in-out infinite, labelFadeIn 0.4s ease forwards`,
        }}
      >
        <style>{`
          @keyframes labelFloat${floatIdx} {
            0%,100% { transform: ${hovered ? "scale(1.08)" : "scale(1)"} translateY(0px); }
            50%      { transform: ${hovered ? "scale(1.08)" : "scale(1)"} translateY(-4px); }
          }
          @keyframes labelFadeIn {
            from { opacity: 0; transform: scale(0.85); }
            to   { opacity: 1; transform: scale(1); }
          }
        `}</style>

        {/* Corner brackets */}
        <div style={{
          position: "absolute", top: 0, left: 0,
          width: 8, height: 8,
          borderTop: `2px solid ${hex}`,
          borderLeft: `2px solid ${hex}`,
          borderRadius: "8px 0 0 0",
        }} />
        <div style={{
          position: "absolute", bottom: 0, right: 0,
          width: 8, height: 8,
          borderBottom: `2px solid ${hex}`,
          borderRight: `2px solid ${hex}`,
          borderRadius: "0 0 8px 0",
        }} />

        {/* Title row */}
        <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: hovered ? 7 : 3 }}>
          <span style={{ fontSize: 12 }}>{icon}</span>
          <span style={{ fontWeight: 900, color: hex, fontSize: hovered ? 12 : 11, letterSpacing: 0.4 }}>
            {name.toUpperCase()}
          </span>
        </div>

        {/* Health bar */}
        <div style={{
          background: "rgba(255,255,255,0.06)",
          borderRadius: 2, height: 3,
          marginBottom: hovered ? 7 : 0,
          overflow: "hidden",
        }}>
          <div style={{
            width: `${comp.health}%`, height: "100%", borderRadius: 2,
            background: `linear-gradient(90deg, ${hc}88, ${hc})`,
            boxShadow: `0 0 4px ${hc}`,
            transition: "width 0.6s ease",
          }} />
        </div>

        {hovered ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {[
              { label: "Health",     val: `${comp.health}%`,              vc: hc   },
              { label: "Failure",    val: `${fp}%`,                       vc: fpC  },
              { label: "RUL",        val: `${comp.rul}d`,                 vc: "#94a3b8" },
              { label: "Confidence", val: `${Math.round(comp.confidence)}%`, vc: "#38bdf8" },
            ].map(({ label, val, vc }) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <span style={{ fontSize: 10, color: "#475569" }}>{label}</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: vc }}>{val}</span>
              </div>
            ))}
            <div style={{
              marginTop: 3, fontSize: 9, color: hc,
              textAlign: "center", fontWeight: 700,
              padding: "2px 0", borderTop: `1px solid ${hex}22`,
            }}>
              {comp.status}
            </div>
          </div>
        ) : (
          <div style={{ color: hc, fontWeight: 900, fontSize: 13, marginTop: 1, textAlign: "center" }}>
            {comp.health}%
          </div>
        )}
      </div>
    </Html>
  );
}

interface Props {
  twinData:         Record<string, ComponentState>;
  colors:           Record<string, THREE.Color>;
  hoveredComponent: string | null;
  onComponentClick: (name: string) => void;
}

export default function FloatingLabels({ twinData, colors, hoveredComponent, onComponentClick }: Props) {
  return (
    <>
      {REGISTRY.map(({ id, name, icon, modelPosition }, idx) => {
        const comp = twinData[id];
        if (!comp) return null;
        // Place label above the 3D model
        const pos: [number, number, number] = [modelPosition[0], modelPosition[1] + 1.1, modelPosition[2]];
        return (
          <Label
            key={id}
            position={pos}
            name={name}
            icon={icon}
            comp={comp}
            hovered={hoveredComponent === name}
            color={colors[id] ?? new THREE.Color("#38bdf8")}
            onClick={() => onComponentClick(name)}
            floatIdx={idx}
          />
        );
      })}
    </>
  );
}

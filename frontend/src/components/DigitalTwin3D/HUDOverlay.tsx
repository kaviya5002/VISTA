/**
 * HUDOverlay — Premium holographic HUD
 *
 * Each component gets:
 *   • A billboard card (always faces camera via Html distanceFactor)
 *   • A 3D callout line from hotspot → card anchor
 *   • Animated pulsing border (health-colored)
 *   • Live health bar with glow
 *   • 6 sensor metrics: Health, Failure%, RUL, Confidence, Voltage/Temp/RPM
 *   • Critical pulse animation
 *   • Floating up/down animation
 *
 * Reads all positions from ComponentRegistry — nothing hardcoded.
 */

import { useRef, useMemo } from "react";
import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { REGISTRY } from "./ComponentRegistry";
import type { TwinData, ComponentState } from "./useTwinAnimation";

// ── HUD anchor positions (further out than hotspots, spread around vehicle) ──
const HUD_OFFSETS: Record<string, [number, number, number]> = {
  battery:      [-3.2, 1.4,  1.0],
  motor:        [ 3.2, 1.4, -1.8],
  cooling:      [ 0.0, 3.0, -2.8],
  brakes:       [-3.2, 0.8,  2.0],
  electrical:   [ 3.2, 1.8,  0.2],
  transmission: [ 3.2, 1.0, -0.6],
};

function hc(health: number) {
  return health >= 75 ? "#00ffcc" : health >= 45 ? "#f59e0b" : "#ef4444";
}
function fc(fp: number) {
  return fp > 0.6 ? "#ef4444" : fp > 0.35 ? "#f59e0b" : "#22c55e";
}

// ── 3D callout line from hotspot to HUD card ─────────────────────────────────

interface CalloutLineProps {
  from:    [number, number, number];
  to:      [number, number, number];
  color:   string;
  health:  number;
}

function CalloutLine({ from, to, color, health }: CalloutLineProps) {
  const ref = useRef<THREE.Line>(null);

  const points = useMemo(() => {
    const a = new THREE.Vector3(...from);
    const b = new THREE.Vector3(...to);
    // Elbow: go up first, then across
    const mid = new THREE.Vector3(a.x, b.y, a.z);
    return [a, mid, b];
  }, [from, to]);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    return geo;
  }, [points]);

  const material = useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: 0.55,
        depthWrite: false,
      }),
    [color]
  );

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const speed = health < 35 ? 4 : health < 60 ? 2 : 1;
    (ref.current.material as THREE.LineBasicMaterial).opacity =
      0.35 + Math.sin(clock.elapsedTime * speed) * 0.25;
  });

  return <primitive object={new THREE.Line(geometry, material)} ref={ref} />;
}

// ── Sensor row inside HUD card ────────────────────────────────────────────────

function SRow({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "2px 0",
      borderBottom: "1px solid rgba(255,255,255,0.04)",
    }}>
      <span style={{ fontSize: 9, color: "#475569", letterSpacing: 0.3 }}>{label}</span>
      <span style={{ fontSize: 10, fontWeight: 700, color, fontFamily: "monospace" }}>{value}</span>
    </div>
  );
}

// ── Individual HUD card ───────────────────────────────────────────────────────

interface CardProps {
  id:         string;
  name:       string;
  icon:       string;
  comp:       ComponentState;
  hotspot:    [number, number, number];
  hudPos:     [number, number, number];
  isCritical: boolean;
  isHovered:  boolean;
  isSelected: boolean;
  onClick:    () => void;
  onHover:    (id: string | null) => void;
}

function HUDCard({
  id, name, icon, comp, hotspot, hudPos,
  isCritical, isHovered, isSelected, onClick, onHover,
}: CardProps) {
  const health = comp.health;
  const fp     = comp.failure_probability;
  const color  = hc(health);
  const fpCol  = fc(fp);

  // Sensor display — pull from sensors dict or derive
  const sensors = comp.sensors ?? {};
  const voltage  = sensors.voltage     != null ? `${Number(sensors.voltage).toFixed(1)}V`     : null;
  const temp     = sensors.temperature != null ? `${Number(sensors.temperature).toFixed(1)}°C` : null;
  const rpm      = sensors.rpm         != null ? `${Math.round(Number(sensors.rpm))}rpm`       : null;

  const active = isHovered || isSelected;

  return (
    <>
      {/* 3D callout line */}
      <CalloutLine from={hotspot} to={hudPos} color={color} health={health} />

      {/* Billboard card */}
      <Html
        position={hudPos}
        center
        distanceFactor={8}
        zIndexRange={[10, 0]}
      >
        <div
          onPointerEnter={() => onHover(name)}
          onPointerLeave={() => onHover(null)}
          onClick={onClick}
          style={{
            position: "relative",
            background: active
              ? "rgba(5,7,14,0.98)"
              : "rgba(5,7,14,0.88)",
            border: `1px solid ${active ? color : color + "55"}`,
            borderRadius: 9,
            padding: "8px 11px",
            minWidth: active ? 148 : 118,
            fontFamily: "monospace",
            cursor: "pointer",
            transition: "all 0.22s cubic-bezier(0.4,0,0.2,1)",
            transform: active ? "scale(1.06)" : "scale(1)",
            boxShadow: active
              ? `0 0 22px ${color}55, 0 0 6px ${color}33, inset 0 0 12px ${color}08`
              : `0 0 10px ${color}22`,
            animation: isCritical
              ? "hudCritPulse 1.1s ease-in-out infinite"
              : "hudFloat 3s ease-in-out infinite",
          }}
        >
          <style>{`
            @keyframes hudFloat {
              0%,100% { transform: ${active ? "scale(1.06)" : "scale(1)"} translateY(0px); }
              50%      { transform: ${active ? "scale(1.06)" : "scale(1)"} translateY(-3px); }
            }
            @keyframes hudCritPulse {
              0%,100% { box-shadow: 0 0 14px #ef444444; border-color: #ef444488; }
              50%      { box-shadow: 0 0 28px #ef444466; border-color: #ef4444cc; }
            }
          `}</style>

          {/* Corner accent — top-left */}
          <div style={{
            position: "absolute", top: 0, left: 0,
            width: 10, height: 10,
            borderTop: `2px solid ${color}`,
            borderLeft: `2px solid ${color}`,
            borderRadius: "9px 0 0 0",
          }} />
          {/* Corner accent — bottom-right */}
          <div style={{
            position: "absolute", bottom: 0, right: 0,
            width: 10, height: 10,
            borderBottom: `2px solid ${color}`,
            borderRight: `2px solid ${color}`,
            borderRadius: "0 0 9px 0",
          }} />

          {/* Title */}
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 5 }}>
            <span style={{ fontSize: 12 }}>{icon}</span>
            <span style={{ fontSize: 11, fontWeight: 900, color, letterSpacing: 0.5 }}>
              {name.toUpperCase()}
            </span>
            {isCritical && (
              <span style={{
                marginLeft: "auto", fontSize: 8, color: "#ef4444",
                fontWeight: 700, padding: "1px 4px",
                border: "1px solid #ef444466", borderRadius: 3,
                animation: "hudCritPulse 1.1s ease-in-out infinite",
              }}>CRIT</span>
            )}
          </div>

          {/* Health bar */}
          <div style={{
            background: "rgba(255,255,255,0.06)",
            borderRadius: 2, height: 4, marginBottom: 6,
            overflow: "hidden",
          }}>
            <div style={{
              width: `${health}%`, height: "100%", borderRadius: 2,
              background: `linear-gradient(90deg, ${color}88, ${color})`,
              boxShadow: `0 0 6px ${color}`,
              transition: "width 0.6s ease",
            }} />
          </div>

          {/* Primary metric */}
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 18, fontWeight: 900, color, lineHeight: 1 }}>{health}%</div>
              <div style={{ fontSize: 8, color: "#334155", marginTop: 1 }}>HEALTH</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: fpCol, lineHeight: 1 }}>
                {Math.round(fp * 100)}%
              </div>
              <div style={{ fontSize: 8, color: "#334155", marginTop: 1 }}>FAIL</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#38bdf8", lineHeight: 1 }}>
                {comp.rul}d
              </div>
              <div style={{ fontSize: 8, color: "#334155", marginTop: 1 }}>RUL</div>
            </div>
          </div>

          {/* Expanded sensor rows on hover/select */}
          {active && (
            <div style={{ borderTop: `1px solid ${color}22`, paddingTop: 5, marginTop: 2 }}>
              <SRow label="AI Confidence" value={`${Math.round(comp.confidence)}%`} color="#38bdf8" />
              {voltage && <SRow label="Voltage"     value={voltage} color="#a78bfa" />}
              {temp    && <SRow label="Temperature" value={temp}    color={Number(sensors.temperature) > 90 ? "#ef4444" : "#f59e0b"} />}
              {rpm     && <SRow label="RPM"         value={rpm}     color="#22c55e" />}
              <div style={{
                marginTop: 5, fontSize: 9, color,
                textAlign: "center", fontWeight: 700,
                padding: "2px 0",
              }}>
                {comp.status === "Critical" ? "⚠ IMMEDIATE ACTION" :
                 comp.status === "Warning"  ? "⚡ MONITOR CLOSELY" :
                                              "✓ NOMINAL"}
              </div>
            </div>
          )}
        </div>
      </Html>
    </>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

interface Props {
  twinData:         TwinData;
  hoveredComponent: string | null;
  selectedComponent: string | null;
  onComponentClick: (name: string) => void;
  onHover:          (name: string | null) => void;
}

export default function HUDOverlay({
  twinData, hoveredComponent, selectedComponent, onComponentClick, onHover,
}: Props) {
  const critSet = new Set(twinData.critical_components.map(c => c.toLowerCase()));

  return (
    <>
      {REGISTRY.map(({ id, name, icon, hotspot }) => {
        const comp   = (twinData as any)[id] as ComponentState | undefined;
        const hudPos = HUD_OFFSETS[id];
        if (!comp || !hudPos) return null;
        // Only render HUD card when hovered or selected — keeps car as hero
        const isHov = hoveredComponent === name;
        const isSel = selectedComponent === name;
        if (!isHov && !isSel) return null;

        return (
          <HUDCard
            key={id}
            id={id}
            name={name}
            icon={icon}
            comp={comp}
            hotspot={hotspot}
            hudPos={hudPos}
            isCritical={critSet.has(id)}
            isHovered={isHov}
            isSelected={isSel}
            onClick={() => onComponentClick(name)}
            onHover={onHover}
          />
        );
      })}
    </>
  );
}

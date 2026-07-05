/**
 * TimelineControls
 * ─────────────────────────────────────────────────────────────────────────────
 * Premium industrial-grade timeline panel.
 *
 * Layout (top → bottom):
 *   • Header row  — "AI Timeline Forecast" + day badge
 *   • Transport   — Reset | Play/Pause | day counter
 *   • Slider      — draggable, gradient fill, tick marks at 0/7/15/30
 *   • Delta cards — Health Δ, Battery Δ, Failure Δ, RUL Δ
 *   • Status line — predicted vehicle state at selected day
 *
 * All values come from the parent via props — this component is pure UI.
 */

import { useRef, useCallback } from "react";
import type { TwinData } from "../DigitalTwin3D";

interface Props {
  day:            number;
  playing:        boolean;
  forecastLoading: boolean;
  today:          TwinData | null;
  future:         TwinData | null;   // interpolated at `day`, null when day===0
  onDayChange:    (day: number) => void;
  onPlay:         () => void;
  onPause:        () => void;
  onReset:        () => void;
}

const MARKS = [0, 7, 15, 30] as const;

function hc(h: number) {
  return h >= 75 ? "#22c55e" : h >= 45 ? "#f59e0b" : "#ef4444";
}

// ─── Transport button ─────────────────────────────────────────────────────────
function TBtn({
  icon, label, active, onClick,
}: { icon: string; label: string; active?: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      title={label}
      style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        width: 32, height: 32, borderRadius: 8, cursor: "pointer",
        background: active ? "rgba(56,189,248,0.15)" : "rgba(255,255,255,0.04)",
        border: `1px solid ${active ? "rgba(56,189,248,0.35)" : "rgba(255,255,255,0.08)"}`,
        color: active ? "#38bdf8" : "#64748b",
        fontSize: 14, transition: "all 0.15s",
      }}
    >
      {icon}
    </button>
  );
}

// ─── Delta card ───────────────────────────────────────────────────────────────
function DeltaCard({
  label, now, future, unit, invert,
}: { label: string; now: number; future: number; unit: string; invert: boolean }) {
  const delta = future - now;
  const bad   = invert ? delta < 0 : delta > 0;
  const good  = invert ? delta > 0 : delta < 0;
  const color = delta === 0 ? "#475569" : bad ? "#ef4444" : good ? "#22c55e" : "#f59e0b";
  const arrow = delta === 0 ? "─" : delta > 0 ? "▲" : "▼";

  return (
    <div style={{
      flex: "1 1 0", minWidth: 0,
      background: "rgba(255,255,255,0.025)",
      border: `1px solid ${color}22`,
      borderRadius: 7, padding: "6px 8px",
    }}>
      <div style={{ fontSize: 9, color: "#475569", marginBottom: 3, textTransform: "uppercase", letterSpacing: 0.8 }}>
        {label}
      </div>
      <div style={{ fontSize: 13, fontWeight: 800, color, fontFamily: "monospace", lineHeight: 1 }}>
        {arrow} {Math.abs(delta)}{unit}
      </div>
      <div style={{ fontSize: 9, color: "#334155", marginTop: 2, fontFamily: "monospace" }}>
        {now}{unit} → {future}{unit}
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function TimelineControls({
  day, playing, forecastLoading,
  today, future,
  onDayChange, onPlay, onPause, onReset,
}: Props) {
  const trackRef = useRef<HTMLDivElement>(null);

  // Pointer-drag on the slider track
  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    const track = trackRef.current;
    if (!track) return;
    e.currentTarget.setPointerCapture(e.pointerId);

    const move = (ev: PointerEvent) => {
      const rect = track.getBoundingClientRect();
      const t    = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
      onDayChange(Math.round(t * 30));
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup",   up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup",   up);
    move(e.nativeEvent);
  }, [onDayChange]);

  const pct        = (day / 30) * 100;
  const vh         = future?.vehicle_health ?? today?.vehicle_health ?? 85;
  const thumbColor = day === 0 ? "#38bdf8" : hc(vh);
  const fillColor  = `linear-gradient(90deg, #38bdf8 0%, ${thumbColor} 100%)`;

  return (
    <div style={{
      background: "rgba(5,7,12,0.97)",
      border: "1px solid rgba(56,189,248,0.14)",
      borderRadius: 12,
      padding: "14px 16px",
      userSelect: "none",
      fontFamily: "system-ui, sans-serif",
    }}>

      {/* ── Header ── */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <span style={{ fontSize: 9, color: "#475569", textTransform: "uppercase", letterSpacing: 1.2 }}>
            AI Timeline
          </span>
          {forecastLoading && (
            <span style={{ fontSize: 9, color: "#f59e0b" }}>loading…</span>
          )}
        </div>
        <span style={{
          fontSize: 11, fontWeight: 800, fontFamily: "monospace",
          color: day === 0 ? "#38bdf8" : thumbColor,
          padding: "2px 9px", borderRadius: 8,
          background: day === 0 ? "rgba(56,189,248,0.1)" : thumbColor + "18",
          border: `1px solid ${day === 0 ? "rgba(56,189,248,0.25)" : thumbColor + "44"}`,
          transition: "all 0.3s",
        }}>
          {day === 0 ? "LIVE" : `+${day}d`}
        </span>
      </div>

      {/* ── Transport controls ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <TBtn icon="⏮" label="Reset"      onClick={onReset} />
        {playing
          ? <TBtn icon="⏸" label="Pause" active onClick={onPause} />
          : <TBtn icon="▶" label="Play"  active={day < 30} onClick={onPlay} />
        }
        <div style={{ flex: 1 }} />
        <span style={{
          fontSize: 11, fontFamily: "monospace", color: "#64748b",
          background: "rgba(255,255,255,0.04)", padding: "3px 8px",
          borderRadius: 6, border: "1px solid rgba(255,255,255,0.06)",
        }}>
          Day {day} / 30
        </span>
      </div>

      {/* ── Slider track ── */}
      <div
        ref={trackRef}
        onPointerDown={handlePointerDown}
        style={{ position: "relative", height: 32, cursor: "pointer", marginBottom: 2 }}
      >
        {/* Rail */}
        <div style={{
          position: "absolute", top: "50%", left: 0, right: 0,
          height: 4, transform: "translateY(-50%)",
          background: "rgba(255,255,255,0.06)", borderRadius: 2,
        }} />

        {/* Filled portion */}
        <div style={{
          position: "absolute", top: "50%", left: 0,
          width: `${pct}%`, height: 4, transform: "translateY(-50%)",
          background: fillColor, borderRadius: 2,
          transition: "width 0.08s",
        }} />

        {/* Tick marks */}
        {MARKS.map(m => (
          <div
            key={m}
            onClick={e => { e.stopPropagation(); onDayChange(m); }}
            style={{
              position: "absolute", top: "50%",
              left: `${(m / 30) * 100}%`,
              transform: "translate(-50%, -50%)",
              width: m === day ? 10 : 6,
              height: m === day ? 10 : 6,
              borderRadius: "50%",
              background: m === day ? thumbColor : "rgba(255,255,255,0.12)",
              border: m === day ? `2px solid #05070a` : "none",
              boxShadow: m === day ? `0 0 8px ${thumbColor}88` : "none",
              transition: "all 0.2s",
              cursor: "pointer",
              zIndex: 2,
            }}
          />
        ))}

        {/* Thumb */}
        <div style={{
          position: "absolute", top: "50%",
          left: `${pct}%`,
          transform: "translate(-50%, -50%)",
          width: 20, height: 20, borderRadius: "50%",
          background: thumbColor,
          border: "3px solid #05070a",
          boxShadow: `0 0 14px ${thumbColor}99`,
          transition: "left 0.08s, background 0.3s, box-shadow 0.3s",
          zIndex: 3,
        }} />
      </div>

      {/* Tick labels */}
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        {MARKS.map(m => (
          <span
            key={m}
            onClick={() => onDayChange(m)}
            style={{
              fontSize: 9, fontFamily: "monospace", cursor: "pointer",
              color: day === m ? "#94a3b8" : "#2d3f55",
              transition: "color 0.2s",
            }}
          >
            {m === 0 ? "Today" : `+${m}d`}
          </span>
        ))}
      </div>

      {/* ── Delta cards — only when day > 0 and data available ── */}
      {day > 0 && today && future && (
        <>
          <div style={{ display: "flex", gap: 5, marginBottom: 8 }}>
            <DeltaCard
              label="Health"
              now={today.vehicle_health}
              future={future.vehicle_health}
              unit="%"
              invert
            />
            <DeltaCard
              label="Battery"
              now={today.battery.health}
              future={future.battery.health}
              unit="%"
              invert
            />
            <DeltaCard
              label="Failure"
              now={Math.round(today.battery.failure_probability * 100)}
              future={Math.round(future.battery.failure_probability * 100)}
              unit="%"
              invert={false}
            />
            <DeltaCard
              label="RUL"
              now={today.battery.rul}
              future={future.battery.rul}
              unit="d"
              invert
            />
          </div>

          {/* Status prediction line */}
          <div style={{
            padding: "6px 10px", borderRadius: 7,
            background: thumbColor + "10",
            border: `1px solid ${thumbColor}30`,
            fontSize: 10, color: thumbColor, fontWeight: 700,
            transition: "all 0.3s",
          }}>
            {future.vehicle_status === "Critical"
              ? `⚠ Predicted CRITICAL state at +${day} days`
              : future.vehicle_status === "Warning"
              ? `⚡ Degrading — Warning state at +${day} days`
              : `✓ Vehicle remains Healthy at +${day} days`}
          </div>
        </>
      )}

      {/* Forecast unavailable notice */}
      {day > 0 && !future && !forecastLoading && (
        <div style={{ fontSize: 10, color: "#334155", textAlign: "center", padding: "6px 0" }}>
          Forecast data unavailable
        </div>
      )}
    </div>
  );
}

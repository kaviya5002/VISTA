/**
 * VehicleDigitalTwin — embeds the full holographic DigitalTwinScene
 * inside the Vehicle Details "Digital Twin" tab.
 *
 * Fetches live data for the given vehicleId via useLiveTwin.
 * Supports timeline forecast via useTimelineState.
 * All component models, connection beams, hotspots, labels, popups,
 * bloom, scan line, and camera controls are fully active.
 */
import { useState, useEffect } from "react";
import { DigitalTwinScene, TimelineControls, type CameraMode } from "./DigitalTwin3D";
import { useLiveTwin }      from "../hooks/useLiveTwin";
import { useTimelineState } from "../hooks/useTimelineState";
import { REGISTRY }         from "./DigitalTwin3D/ComponentRegistry";

interface Props { vehicleId: number; }

const CAMERA_BUTTONS: { mode: CameraMode; label: string; icon: string }[] = [
  { mode: "overview", label: "Overview", icon: "🌐" },
  { mode: "top",      label: "Top",      icon: "⬆️" },
  { mode: "battery",  label: "Battery",  icon: "🔋" },
  { mode: "motor",    label: "Motor",    icon: "⚙️" },
  { mode: "cooling",  label: "Cooling",  icon: "❄️" },
  { mode: "auto",     label: "Auto",     icon: "▶️" },
];

export default function VehicleDigitalTwin({ vehicleId }: Props) {
  const [cameraMode,    setCameraMode]    = useState<CameraMode>("overview");
  const [showLabels,    setShowLabels]    = useState(true);
  const [showParticles, setShowParticles] = useState(true);

  const { twinData, loading, error } = useLiveTwin(vehicleId);

  const {
    day, playing, forecastLoading,
    displayData, setDay, play, pause, reset,
  } = useTimelineState(vehicleId, twinData);

  // Reset timeline when vehicle changes
  useEffect(() => { reset(); }, [vehicleId]); // eslint-disable-line react-hooks/exhaustive-deps

  const activeData    = displayData ?? twinData;
  const isForecasting = day > 0;
  const statusColor   = activeData?.vehicle_status === "Healthy" ? "#22c55e"
    : activeData?.vehicle_status === "Warning" ? "#f59e0b" : "#ef4444";

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      height: "80vh", minHeight: 600,
      background: "#05070A", borderRadius: 12, overflow: "hidden",
      border: "1px solid rgba(56,189,248,0.1)",
    }}>

      {/* ── Top bar ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 16px", flexShrink: 0,
        background: "rgba(5,7,10,0.95)",
        borderBottom: `1px solid ${isForecasting ? "rgba(245,158,11,0.2)" : "rgba(56,189,248,0.1)"}`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 800, color: "#38bdf8" }}>
            ⚡ Digital Twin · Vehicle {vehicleId}
          </span>
          {isForecasting ? (
            <span style={{
              fontSize: 10, padding: "2px 8px", borderRadius: 8,
              background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)",
              color: "#f59e0b", fontWeight: 700,
            }}>🔮 Forecast +{day}d</span>
          ) : (
            <span style={{
              fontSize: 10, padding: "2px 8px", borderRadius: 8,
              background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)",
              color: "#22c55e", fontWeight: 700,
            }}>● LIVE</span>
          )}
          {activeData && (
            <span style={{
              fontSize: 10, padding: "2px 8px", borderRadius: 8,
              background: statusColor + "18", border: `1px solid ${statusColor}44`,
              color: statusColor, fontWeight: 700,
            }}>{activeData.vehicle_status} · {activeData.vehicle_health}%</span>
          )}
          {error && (
            <span style={{ fontSize: 10, color: "#ef4444" }}>{error}</span>
          )}
        </div>

        <div style={{ display: "flex", gap: 6 }}>
          {[
            { label: "Labels",    value: showLabels,    set: setShowLabels    },
            { label: "Particles", value: showParticles, set: setShowParticles },
          ].map(({ label, value, set }) => (
            <button key={label} onClick={() => set(v => !v)} style={{
              fontSize: 10, padding: "3px 9px", borderRadius: 6, cursor: "pointer",
              background: value ? "rgba(56,189,248,0.1)" : "rgba(255,255,255,0.04)",
              border: `1px solid ${value ? "rgba(56,189,248,0.25)" : "rgba(255,255,255,0.08)"}`,
              color: value ? "#38bdf8" : "#64748b",
            }}>{label}</button>
          ))}
        </div>
      </div>

      {/* ── Main layout ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* Left sidebar — camera + components */}
        <div style={{
          width: 170, flexShrink: 0,
          background: "rgba(5,7,10,0.9)",
          borderRight: "1px solid rgba(56,189,248,0.08)",
          display: "flex", flexDirection: "column", overflowY: "auto",
          padding: "12px 10px",
        }}>
          {/* Camera buttons */}
          <div style={{ fontSize: 9, color: "#475569", marginBottom: 7, textTransform: "uppercase", letterSpacing: 1.2 }}>Camera</div>
          {CAMERA_BUTTONS.map(({ mode, label, icon }) => (
            <button key={mode} onClick={() => setCameraMode(mode)} style={{
              width: "100%", padding: "5px 8px", borderRadius: 6, cursor: "pointer",
              textAlign: "left", marginBottom: 3, display: "flex", alignItems: "center", gap: 6,
              background: cameraMode === mode ? "rgba(56,189,248,0.1)" : "rgba(255,255,255,0.02)",
              border: `1px solid ${cameraMode === mode ? "rgba(56,189,248,0.25)" : "rgba(255,255,255,0.05)"}`,
              color: cameraMode === mode ? "#38bdf8" : "#64748b",
              fontSize: 10, fontWeight: cameraMode === mode ? 700 : 400,
            }}>
              <span>{icon}</span>{label}
            </button>
          ))}

          {/* Component health bars */}
          {activeData && (
            <>
              <div style={{ fontSize: 9, color: "#475569", margin: "14px 0 7px", textTransform: "uppercase", letterSpacing: 1.2 }}>Components</div>
              {REGISTRY.map(({ id, name, icon }) => {
                const comp  = (activeData as any)[id];
                if (!comp) return null;
                const color = comp.health >= 75 ? "#22c55e" : comp.health >= 45 ? "#f59e0b" : "#ef4444";
                return (
                  <div key={id} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                      <span style={{ fontSize: 10, color: "#94a3b8" }}>{icon} {name}</span>
                      <span style={{ fontSize: 10, fontWeight: 700, color }}>{comp.health}%</span>
                    </div>
                    <div style={{ background: "#0f172a", borderRadius: 3, height: 3 }}>
                      <div style={{
                        width: `${comp.health}%`, background: color,
                        height: "100%", borderRadius: 3, transition: "width 0.5s",
                      }} />
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>

        {/* 3D Canvas */}
        <div style={{ flex: 1, position: "relative" }}>
          {loading && (
            <div style={{
              position: "absolute", inset: 0, zIndex: 10,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "rgba(5,7,10,0.85)",
            }}>
              <div style={{
                width: 32, height: 32,
                border: "3px solid rgba(56,189,248,0.2)",
                borderTop: "3px solid #38bdf8",
                borderRadius: "50%", animation: "spin 0.8s linear infinite",
              }} />
              <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
            </div>
          )}

          {isForecasting && (
            <div style={{
              position: "absolute", inset: 0, zIndex: 1, pointerEvents: "none",
              background: "linear-gradient(180deg, rgba(245,158,11,0.04) 0%, transparent 30%)",
              borderTop: "2px solid rgba(245,158,11,0.2)",
            }} />
          )}

          <DigitalTwinScene
            twinData={twinData}
            timelineTwinData={displayData}
            showLabels={showLabels}
            showParticles={showParticles}
            cameraMode={cameraMode}
            onCameraModeChange={setCameraMode}
          />

          {!loading && activeData && (
            <div style={{
              position: "absolute", bottom: 12, left: "50%", transform: "translateX(-50%)",
              fontSize: 10, color: "#334155", pointerEvents: "none",
              background: "rgba(5,7,10,0.6)", padding: "3px 10px",
              borderRadius: 20, border: "1px solid rgba(255,255,255,0.05)", whiteSpace: "nowrap",
            }}>
              {isForecasting
                ? `🔮 Forecast +${day}d — drag slider to explore`
                : "Click a component · Drag to orbit · Scroll to zoom"}
            </div>
          )}
        </div>

        {/* Right sidebar — timeline */}
        <div style={{
          width: 210, flexShrink: 0,
          background: "rgba(5,7,10,0.9)",
          borderLeft: "1px solid rgba(56,189,248,0.08)",
          overflowY: "auto", padding: "12px 10px",
        }}>
          <TimelineControls
            day={day}
            playing={playing}
            forecastLoading={forecastLoading}
            today={twinData}
            future={displayData}
            onDayChange={setDay}
            onPlay={play}
            onPause={pause}
            onReset={reset}
          />
        </div>
      </div>
    </div>
  );
}

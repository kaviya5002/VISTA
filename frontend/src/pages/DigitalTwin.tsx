import { useState, useEffect, useRef } from "react";
import { DigitalTwinScene, TimelineControls, type CameraMode } from "../components/DigitalTwin3D";
import { useLiveTwin }       from "../hooks/useLiveTwin";
import { useTimelineState }  from "../hooks/useTimelineState";
import { useDemoMode }       from "../hooks/useDemoMode";
import { REGISTRY }          from "../components/DigitalTwin3D/ComponentRegistry";

// ─── Animated counter ─────────────────────────────────────────────────────────
function useAnimatedValue(target: number, decimals = 1) {
  const [display, setDisplay] = useState(target);
  const cur = useRef(target);
  useEffect(() => {
    let raf: number;
    const step = () => {
      const diff = target - cur.current;
      if (Math.abs(diff) < 0.01) { setDisplay(target); return; }
      cur.current += diff * 0.12;
      setDisplay(parseFloat(cur.current.toFixed(decimals)));
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, decimals]);
  return display;
}

function SensorRow({
  label, value, unit, color,
}: { label: string; value: number; unit: string; color: string }) {
  const v = useAnimatedValue(value, unit === "rpm" ? 0 : 1);
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "5px 0", borderBottom: "1px solid rgba(255,255,255,0.04)",
    }}>
      <span style={{ fontSize: 11, color: "#64748b" }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 700, color, fontFamily: "monospace" }}>
        {unit === "rpm" ? Math.round(v) : v.toFixed(1)}
        <span style={{ fontSize: 10, color: "#475569", marginLeft: 2 }}>{unit}</span>
      </span>
    </div>
  );
}

function PipelineStep({ label, value, active }: { label: string; value: string; active: boolean }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "5px 8px", borderRadius: 5, marginBottom: 3,
      background: active ? "rgba(56,189,248,0.08)" : "transparent",
      border: `1px solid ${active ? "rgba(56,189,248,0.2)" : "transparent"}`,
      transition: "all 0.3s",
    }}>
      <span style={{ fontSize: 10, color: active ? "#94a3b8" : "#475569" }}>{label}</span>
      <span style={{ fontSize: 10, fontWeight: 700, color: active ? "#38bdf8" : "#334155", fontFamily: "monospace" }}>{value}</span>
    </div>
  );
}

const CAMERA_BUTTONS: { mode: CameraMode; label: string; icon: string }[] = [
  { mode: "overview", label: "Overview",  icon: "🌐" },
  { mode: "top",      label: "Top",       icon: "⬆️" },
  { mode: "battery",  label: "Battery",   icon: "🔋" },
  { mode: "motor",    label: "Motor",     icon: "⚙️" },
  { mode: "cooling",  label: "Cooling",   icon: "❄️" },
  { mode: "auto",     label: "Auto Tour", icon: "▶️" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function DigitalTwin() {
  const [vehicleId,     setVehicleId]     = useState(1);
  const [cameraMode,    setCameraMode]    = useState<CameraMode>("overview");
  const [showLabels,    setShowLabels]    = useState(true);
  const [showParticles, setShowParticles] = useState(true);
  const [pipelineStep,  setPipelineStep]  = useState(0);

  // ── Live data ──────────────────────────────────────────────────────────────
  const { twinData, loading, isStale, lastUpdated, error } = useLiveTwin(vehicleId);

  // ── Timeline state — single source of truth ────────────────────────────────
  const {
    day, playing, forecastLoading,
    displayData,
    setDay, play, pause, reset,
  } = useTimelineState(vehicleId, twinData);

  // ── Demo mode ──────────────────────────────────────────────────────────────
  const {
    active: demoActive, startDemo, stopDemo,
    progress: demoProgress, phaseLabel: demoPhaseLabel,
  } = useDemoMode(setDay, setCameraMode);

  // The data driving the entire UI: forecast snapshot when day>0, else live
  const activeData = displayData ?? twinData;

  // Cycle AI pipeline animation
  useEffect(() => {
    const t = setInterval(() => setPipelineStep(s => (s + 1) % 6), 900);
    return () => clearInterval(t);
  }, []);

  // Reset timeline when vehicle changes
  useEffect(() => { reset(); }, [vehicleId]); // eslint-disable-line react-hooks/exhaustive-deps

  const statusColor = activeData?.vehicle_status === "Healthy" ? "#22c55e"
    : activeData?.vehicle_status === "Warning" ? "#f59e0b" : "#ef4444";

  // ── Sensor values — animate from live → forecast smoothly ─────────────────
  const voltage     = Number(activeData?.battery.sensors?.voltage     ?? (11.0 + ((activeData?.battery.health ?? 85) / 100) * 1.8));
  const temperature = Number(activeData?.motor.sensors?.temperature   ?? (60   + ((100 - (activeData?.cooling.health ?? 85)) / 100) * 55));
  const rpm         = Number(activeData?.motor.sensors?.rpm           ?? (800  + ((activeData?.motor.health ?? 85) / 100) * 3200));
  const failureRisk = Math.round((activeData?.battery.failure_probability ?? 0) * 100);
  const avgConf     = activeData
    ? Math.round((activeData.battery.confidence + activeData.motor.confidence + activeData.cooling.confidence) / 3)
    : 0;

  const isForecasting = day > 0;

  return (
    <div style={{ background: "#05070A", minHeight: "100vh", display: "flex", flexDirection: "column", fontFamily: "system-ui, sans-serif" }}>

      {/* ── Top bar ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 20px", flexShrink: 0,
        background: "rgba(5,7,10,0.95)", backdropFilter: "blur(12px)",
        borderBottom: `1px solid ${isForecasting ? "rgba(245,158,11,0.2)" : "rgba(56,189,248,0.1)"}`,
        transition: "border-color 0.4s",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 15, fontWeight: 800, color: "#38bdf8", letterSpacing: 0.5 }}>
            ⚡ TwinGuard · Digital Twin
          </span>

          {/* Demo button */}
          <button
            onClick={demoActive ? stopDemo : startDemo}
            style={{
              fontSize: 11, padding: "4px 12px", borderRadius: 8, cursor: "pointer",
              fontWeight: 700, letterSpacing: 0.5,
              background: demoActive
                ? "rgba(168,85,247,0.18)" : "rgba(56,189,248,0.08)",
              border: `1px solid ${demoActive ? "rgba(168,85,247,0.5)" : "rgba(56,189,248,0.2)"}`,
              color: demoActive ? "#c084fc" : "#38bdf8",
              transition: "all 0.25s",
              animation: demoActive ? "demoPulse 2s ease-in-out infinite" : "none",
            }}
          >
            {demoActive ? "⏹ Stop Demo" : "▶ Demo"}
          </button>
          <style>{`@keyframes demoPulse{0%,100%{box-shadow:0 0 0 0 rgba(168,85,247,0)}50%{box-shadow:0 0 0 6px rgba(168,85,247,0.15)}}`}</style>

          {/* Cinematic demo progress bar */}
          {demoActive && (
            <div style={{
              display: "flex", alignItems: "center", gap: 8,
              background: "rgba(168,85,247,0.08)",
              border: "1px solid rgba(168,85,247,0.2)",
              borderRadius: 8, padding: "4px 10px", minWidth: 220,
            }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 9, color: "#c084fc", marginBottom: 3, fontWeight: 700 }}>
                  {demoPhaseLabel}
                </div>
                <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: 2, height: 2 }}>
                  <div style={{
                    width: `${demoProgress}%`, height: "100%", borderRadius: 2,
                    background: "linear-gradient(90deg, #38bdf8, #c084fc, #ef4444)",
                    transition: "width 0.1s",
                  }} />
                </div>
              </div>
            </div>
          )}

          {/* Live / Forecast mode badge */}
          {isForecasting ? (
            <span style={{
              fontSize: 11, padding: "3px 10px", borderRadius: 10,
              background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)",
              color: "#f59e0b", fontWeight: 700,
            }}>
              🔮 Forecast +{day}d
            </span>
          ) : (
            <span style={{
              fontSize: 11, padding: "3px 10px", borderRadius: 10,
              background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)",
              color: "#22c55e", fontWeight: 700,
            }}>
              ● LIVE
            </span>
          )}

          {activeData && (
            <span style={{
              fontSize: 11, padding: "3px 10px", borderRadius: 10,
              background: statusColor + "18", border: `1px solid ${statusColor}44`,
              color: statusColor, fontWeight: 700,
            }}>
              {activeData.vehicle_status} · {activeData.vehicle_health}%
            </span>
          )}

          {isStale && !isForecasting && (
            <span style={{ fontSize: 10, color: "#f59e0b", padding: "2px 8px", borderRadius: 8, background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)" }}>
              ⚠ Stale
            </span>
          )}
          {error && !isStale && (
            <span style={{ fontSize: 10, color: "#ef4444" }}>{error}</span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {lastUpdated && !isForecasting && (
            <span style={{ fontSize: 10, color: "#334155" }}>
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <span style={{ fontSize: 11, color: "#64748b" }}>Vehicle</span>
          <select
            value={vehicleId}
            onChange={e => setVehicleId(Number(e.target.value))}
            style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#f1f5f9", borderRadius: 6, padding: "4px 8px", fontSize: 11 }}
          >
            {Array.from({ length: 20 }, (_, i) => i + 1).map(n => (
              <option key={n} value={n}>#{n}</option>
            ))}
          </select>

          {[
            { label: "Labels",    value: showLabels,    set: setShowLabels    },
            { label: "Particles", value: showParticles, set: setShowParticles },
          ].map(({ label, value, set }) => (
            <button key={label} onClick={() => set(v => !v)} style={{
              fontSize: 11, padding: "4px 10px", borderRadius: 6, cursor: "pointer",
              background: value ? "rgba(56,189,248,0.1)" : "rgba(255,255,255,0.04)",
              border: `1px solid ${value ? "rgba(56,189,248,0.25)" : "rgba(255,255,255,0.08)"}`,
              color: value ? "#38bdf8" : "#64748b",
            }}>{label}</button>
          ))}
        </div>
      </div>

      {/* ── Main layout ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* ── Left sidebar ── */}
        <div style={{
          width: 200, flexShrink: 0,
          background: "rgba(5,7,10,0.9)", backdropFilter: "blur(12px)",
          borderRight: "1px solid rgba(56,189,248,0.08)",
          display: "flex", flexDirection: "column", overflowY: "auto",
        }}>

          {/* Camera */}
          <div style={{ padding: "14px 12px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <div style={{ fontSize: 9, color: "#475569", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1.2 }}>Camera</div>
            {CAMERA_BUTTONS.map(({ mode, label, icon }) => (
              <button key={mode} onClick={() => setCameraMode(mode)} style={{
                width: "100%", padding: "6px 10px", borderRadius: 6, cursor: "pointer",
                textAlign: "left", marginBottom: 3, display: "flex", alignItems: "center", gap: 7,
                background: cameraMode === mode ? "rgba(56,189,248,0.1)" : "rgba(255,255,255,0.02)",
                border: `1px solid ${cameraMode === mode ? "rgba(56,189,248,0.25)" : "rgba(255,255,255,0.05)"}`,
                color: cameraMode === mode ? "#38bdf8" : "#64748b",
                fontSize: 11, fontWeight: cameraMode === mode ? 700 : 400,
              }}>
                <span>{icon}</span>{label}
              </button>
            ))}
          </div>

          {/* Components — driven by registry, reflect activeData */}
          {activeData && (
            <div style={{ padding: "14px 12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <div style={{ fontSize: 9, color: "#475569", textTransform: "uppercase", letterSpacing: 1.2 }}>Components</div>
                {isForecasting && (
                  <span style={{ fontSize: 8, color: "#f59e0b", fontFamily: "monospace" }}>+{day}d</span>
                )}
              </div>
              {REGISTRY.map(({ id, name, icon }) => {
                const comp  = (activeData as any)[id];
                if (!comp) return null;
                const color = comp.health >= 75 ? "#22c55e" : comp.health >= 45 ? "#f59e0b" : "#ef4444";
                const isCrit = activeData.critical_components.map((c: string) => c.toLowerCase()).includes(id);
                return (
                  <div key={id} style={{ marginBottom: 9 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 11, color: isCrit ? "#fca5a5" : "#94a3b8", display: "flex", alignItems: "center", gap: 4 }}>
                        {icon} <span style={{ textTransform: "capitalize" }}>{name}</span>
                      </span>
                      <span style={{ fontSize: 11, fontWeight: 700, color, transition: "color 0.4s" }}>{comp.health}%</span>
                    </div>
                    <div style={{ background: "#0f172a", borderRadius: 3, height: 4 }}>
                      <div style={{
                        width: `${comp.health}%`, background: color,
                        height: "100%", borderRadius: 3,
                        transition: "width 0.5s, background 0.4s",
                      }} />
                    </div>
                  </div>
                );
              })}

              {activeData.critical_components.length > 0 && (
                <div style={{ marginTop: 10, padding: "7px 9px", borderRadius: 6, background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.18)", fontSize: 10, color: "#fca5a5" }}>
                  🚨 {activeData.critical_components.join(", ")}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── 3D Canvas ── */}
        <div style={{ flex: 1, position: "relative" }}>
          {loading && (
            <div style={{ position: "absolute", inset: 0, zIndex: 10, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(5,7,10,0.8)" }}>
              <div style={{ width: 34, height: 34, border: "3px solid rgba(56,189,248,0.2)", borderTop: "3px solid #38bdf8", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
              <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
            </div>
          )}

          {/* Forecast overlay tint */}
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

          {/* Bottom hint */}
          {!loading && activeData && (
            <div style={{
              position: "absolute", bottom: 16, left: "50%", transform: "translateX(-50%)",
              fontSize: 11, color: "#334155", pointerEvents: "none",
              background: "rgba(5,7,10,0.6)", padding: "4px 12px",
              borderRadius: 20, border: "1px solid rgba(255,255,255,0.05)", whiteSpace: "nowrap",
            }}>
              {isForecasting
                ? `🔮 Showing predicted state at +${day} days — drag slider to explore`
                : "Click a component · Drag to orbit · Scroll to zoom"}
            </div>
          )}
        </div>

        {/* ── Right sidebar ── */}
        <div style={{
          width: 230, flexShrink: 0,
          background: "rgba(5,7,10,0.9)", backdropFilter: "blur(12px)",
          borderLeft: "1px solid rgba(56,189,248,0.08)",
          display: "flex", flexDirection: "column", overflowY: "auto",
        }}>

          {/* ── Timeline Controls ── */}
          <div style={{ padding: "12px 12px 0" }}>
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

          {/* ── Live / Forecast Sensors ── */}
          <div style={{ padding: "14px 14px 0", borderTop: "1px solid rgba(255,255,255,0.05)", marginTop: 12 }}>
            <div style={{ fontSize: 9, color: "#475569", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1.2, display: "flex", alignItems: "center", gap: 6 }}>
              {isForecasting ? (
                <>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#f59e0b", display: "inline-block" }} />
                  Forecast Sensors
                </>
              ) : (
                <>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", display: "inline-block", animation: "blink 1.5s infinite" }} />
                  Live Sensors
                </>
              )}
            </div>
            <style>{`@keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}`}</style>

            {activeData ? (
              <>
                <SensorRow label="Voltage"      value={voltage}     unit="V"   color="#38bdf8" />
                <SensorRow label="Temperature"  value={temperature} unit="°C"  color={temperature > 95 ? "#ef4444" : temperature > 80 ? "#f59e0b" : "#22c55e"} />
                <SensorRow label="Motor RPM"    value={rpm}         unit="rpm" color="#a78bfa" />
                <SensorRow label="Failure Risk" value={failureRisk} unit="%"   color={failureRisk > 60 ? "#ef4444" : failureRisk > 35 ? "#f59e0b" : "#22c55e"} />
                <SensorRow label="Health"       value={activeData.vehicle_health} unit="%" color={statusColor} />
              </>
            ) : (
              <div style={{ color: "#334155", fontSize: 11 }}>Connecting…</div>
            )}
          </div>

          {/* ── AI Pipeline ── */}
          <div style={{ padding: "14px 14px" }}>
            <div style={{ fontSize: 9, color: "#475569", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1.2 }}>AI Pipeline</div>
            {[
              { label: "Raw Sensors",    value: "→ Input"   },
              { label: "Health Model",   value: "RF 97%"    },
              { label: "Failure Model",  value: "XGB 94%"   },
              { label: "Root Cause",     value: "→ Isolate" },
              { label: "RUL Engine",     value: "→ Days"    },
              { label: "Recommendation", value: "→ Action"  },
            ].map(({ label, value }, i) => (
              <PipelineStep key={label} label={label} value={value} active={pipelineStep === i} />
            ))}

            {activeData && (
              <div style={{ marginTop: 12, padding: "8px 10px", borderRadius: 7, background: "rgba(56,189,248,0.06)", border: "1px solid rgba(56,189,248,0.12)" }}>
                <div style={{ fontSize: 10, color: "#475569", marginBottom: 4 }}>Avg Confidence</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: "#38bdf8", fontFamily: "monospace", transition: "all 0.4s" }}>{avgConf}%</div>
                <div style={{ fontSize: 10, color: "#334155", marginTop: 2 }}>Random Forest · XGBoost</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

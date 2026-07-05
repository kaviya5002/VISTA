import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import { getCached, setCached } from "../store/fleetStore";

interface VehicleFrame {
  vehicle_id:          number;
  time:                string;
  health:              number;
  failure_probability: number;
  temperature:         number;
  battery_voltage:     number;
  rpm:                 number;
  status:              string;
  rul:                 number;
}

interface FrameSummary {
  avg_health: number;
  healthy:    number;
  warning:    number;
  critical:   number;
  total:      number;
}

interface ReplayFrame {
  time:     string;
  hour:     number;
  vehicles: VehicleFrame[];
  summary:  FrameSummary;
}

const statusColor = (s: string) =>
  s === "Healthy" ? "lime" : s === "Warning" ? "orange" : "red";

const speedOptions = [0.5, 1, 2, 4];

export default function FleetReplay() {
  const [frames, setFrames]       = useState<ReplayFrame[]>(() => getCached<ReplayFrame[]>("replay") ?? []);
  const [current, setCurrent]     = useState(0);
  const [playing, setPlaying]     = useState(false);
  const [speed, setSpeed]         = useState(1);
  const [loading, setLoading]     = useState(() => !getCached("replay"));
  const [compare, setCompare]     = useState<{a: number; b: number} | null>(null);
  const intervalRef               = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (getCached("replay")) { setLoading(false); return; }
    api.get("/fleet/replay")
      .then(r => {
        setCached("replay", r.data.frames);
        setFrames(r.data.frames);
        setLoading(false);
      })
      .catch(console.error);
  }, []);

  // Playback engine
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (!playing || frames.length === 0) return;

    intervalRef.current = setInterval(() => {
      setCurrent(prev => {
        if (prev >= frames.length - 1) { setPlaying(false); return prev; }
        return prev + 1;
      });
    }, 1000 / speed);

    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [playing, speed, frames.length]);

  const frame   = frames[current];
  const frameA  = compare ? frames[compare.a] : null;
  const frameB  = compare ? frames[compare.b] : null;

  if (loading) return <div style={{ padding: 24, color: "#aaa" }}>⏳ Loading replay data...</div>;
  if (!frame)  return <div style={{ padding: 24, color: "#aaa" }}>No replay data available.</div>;

  return (
    <div style={{ padding: 24, fontFamily: "monospace" }}>
      <Link to="/" style={{ color: "#666" }}>← Dashboard</Link>
      <h1 style={{ margin: "12px 0 4px" }}>⏱ Fleet Replay Engine</h1>
      <p style={{ color: "#666", marginBottom: 24 }}>24-hour fleet health animation</p>

      {/* ── Playback Controls ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24,
                    background: "#111", padding: "14px 20px", borderRadius: 12 }}>
        <button onClick={() => setCurrent(0)}
          style={btn}>⏮</button>
        <button onClick={() => setCurrent(c => Math.max(0, c - 1))}
          style={btn}>⏪</button>
        <button onClick={() => setPlaying(p => !p)}
          style={{ ...btn, background: playing ? "#ef4444" : "#22c55e", minWidth: 80 }}>
          {playing ? "⏸ Pause" : "▶ Play"}
        </button>
        <button onClick={() => setCurrent(c => Math.min(frames.length - 1, c + 1))}
          style={btn}>⏩</button>
        <button onClick={() => setCurrent(frames.length - 1)}
          style={btn}>⏭</button>

        <div style={{ display: "flex", gap: 8, marginLeft: 16 }}>
          {speedOptions.map(s => (
            <button key={s} onClick={() => setSpeed(s)}
              style={{ ...btn, background: speed === s ? "#7c3aed" : "#222" }}>
              {s}×
            </button>
          ))}
        </div>

        <span style={{ marginLeft: "auto", color: "#aaa", fontSize: 14 }}>
          Frame {current + 1} / {frames.length} — {frame.time}
        </span>
      </div>

      {/* ── Timeline Slider ── */}
      <input type="range" min={0} max={frames.length - 1} value={current}
        onChange={e => { setPlaying(false); setCurrent(Number(e.target.value)); }}
        style={{ width: "100%", marginBottom: 24, accentColor: "#7c3aed" }} />

      {/* ── Hour Labels ── */}
      <div style={{ display: "flex", justifyContent: "space-between",
                    marginBottom: 24, fontSize: 11, color: "#555" }}>
        {frames.filter((_, i) => i % 4 === 0).map(f => (
          <span key={f.hour}>{f.time}</span>
        ))}
      </div>

      {/* ── Current Frame Summary ── */}
      <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
        {[
          { label: "Time",         value: frame.time,                  color: "white" },
          { label: "Avg Health",   value: `${frame.summary.avg_health}%`, color: "white" },
          { label: "Healthy",      value: frame.summary.healthy,       color: "lime" },
          { label: "Warning",      value: frame.summary.warning,       color: "orange" },
          { label: "Critical",     value: frame.summary.critical,      color: "red" },
        ].map(s => (
          <div key={s.label} style={statCard}>
            <div style={{ fontSize: 22, fontWeight: "bold", color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 12, color: "#666" }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Health Timeline Bar ── */}
      <div style={{ marginBottom: 28 }}>
        <p style={{ color: "#555", fontSize: 12, marginBottom: 8 }}>Fleet Health Over 24 Hours</p>
        <div style={{ display: "flex", gap: 2, alignItems: "flex-end", height: 60 }}>
          {frames.map((f, i) => (
            <div key={i}
              onClick={() => { setPlaying(false); setCurrent(i); }}
              title={`${f.time} — ${f.summary.avg_health}%`}
              style={{
                flex: 1, cursor: "pointer",
                height: `${f.summary.avg_health}%`,
                background: i === current ? "#7c3aed"
                  : f.summary.avg_health >= 80 ? "#22c55e"
                  : f.summary.avg_health >= 50 ? "#f97316" : "#ef4444",
                borderRadius: 2,
                transition: "height 0.3s ease",
                opacity: i === current ? 1 : 0.6,
              }} />
          ))}
        </div>
      </div>

      {/* ── Compare Tool ── */}
      <div style={{ marginBottom: 28, background: "#111", borderRadius: 12, padding: 16 }}>
        <h3 style={{ marginBottom: 12, color: "#aaa" }}>🔍 Compare Two Moments</h3>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ color: "#666", fontSize: 13 }}>Frame A:
            <input type="number" min={0} max={frames.length - 1}
              defaultValue={0}
              onChange={e => setCompare(c => ({ a: Number(e.target.value), b: c?.b ?? 12 }))}
              style={{ ...numInput, marginLeft: 8 }} />
          </label>
          <label style={{ color: "#666", fontSize: 13 }}>Frame B:
            <input type="number" min={0} max={frames.length - 1}
              defaultValue={12}
              onChange={e => setCompare(c => ({ a: c?.a ?? 0, b: Number(e.target.value) }))}
              style={{ ...numInput, marginLeft: 8 }} />
          </label>
          <button onClick={() => setCompare(compare ? null : { a: 0, b: 12 })}
            style={{ ...btn, background: "#1e3a5f" }}>
            {compare ? "Clear" : "Compare"}
          </button>
        </div>

        {compare && frameA && frameB && (() => {
          const d = {
            health:  round(frameB.summary.avg_health - frameA.summary.avg_health),
            healthy: frameB.summary.healthy  - frameA.summary.healthy,
            warning: frameB.summary.warning  - frameA.summary.warning,
            critical:frameB.summary.critical - frameA.summary.critical,
          };
          return (
            <div style={{ display: "flex", gap: 24, marginTop: 16, flexWrap: "wrap" }}>
              {[
                { label: "Avg Health",  val: `${d.health > 0 ? "+" : ""}${d.health}%`,  color: d.health  >= 0 ? "lime" : "red" },
                { label: "Healthy",     val: `${d.healthy > 0 ? "+" : ""}${d.healthy}`, color: d.healthy >= 0 ? "lime" : "red" },
                { label: "Warning",     val: `${d.warning > 0 ? "+" : ""}${d.warning}`, color: d.warning <= 0 ? "lime" : "orange" },
                { label: "Critical",    val: `${d.critical > 0 ? "+" : ""}${d.critical}`,color: d.critical<= 0 ? "lime" : "red" },
              ].map(item => (
                <div key={item.label} style={statCard}>
                  <div style={{ fontSize: 20, fontWeight: "bold", color: item.color }}>{item.val}</div>
                  <div style={{ fontSize: 11, color: "#555" }}>{frameA.time} → {frameB.time}</div>
                  <div style={{ fontSize: 12, color: "#666" }}>{item.label}</div>
                </div>
              ))}
            </div>
          );
        })()}
      </div>

      {/* ── Vehicle Cards ── */}
      <h3 style={{ marginBottom: 12, color: "#aaa" }}>
        Vehicles at {frame.time}
      </h3>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        {frame.vehicles.slice(0, 20).map(v => (
          <Link key={v.vehicle_id} to={`/vehicle/${v.vehicle_id}`}
            style={{ textDecoration: "none", color: "white" }}>
            <div style={{
              border: `1px solid ${statusColor(v.status)}33`,
              borderRadius: 10, padding: "10px 14px",
              background: "#111", minWidth: 130,
              transition: "all 0.3s ease",
            }}>
              <div style={{ fontWeight: "bold", marginBottom: 4 }}>V-{v.vehicle_id}</div>
              <div style={{ color: statusColor(v.status), fontSize: 12 }}>{v.status}</div>
              <div style={{ fontSize: 12, color: "#555" }}>🔋 {v.health}%</div>
              <div style={{ fontSize: 12, color: "#555" }}>🌡 {v.temperature}°C</div>
              <div style={{ fontSize: 12, color: "#555" }}>⚠ {v.failure_probability}%</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const btn: React.CSSProperties = {
  padding: "8px 14px", borderRadius: 8, border: "none",
  background: "#222", color: "white", cursor: "pointer", fontWeight: "bold",
};

const statCard: React.CSSProperties = {
  background: "#1a1a2e", border: "1px solid #333",
  borderRadius: 10, padding: "12px 18px", textAlign: "center", minWidth: 100,
};

const numInput: React.CSSProperties = {
  width: 60, padding: "4px 8px", borderRadius: 6,
  border: "1px solid #333", background: "#1a1a2e", color: "white",
};

function round(n: number) { return Math.round(n * 10) / 10; }

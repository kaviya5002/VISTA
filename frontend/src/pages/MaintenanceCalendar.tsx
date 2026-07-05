import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api";
import Navbar from "../components/Navbar";
import { getCached, setCached } from "../store/fleetStore";

// ── Types ─────────────────────────────────────────────────────────────────────
interface CalendarEvent {
  vehicle_id: number;
  date: string;
  time: string;
  task: string;
  duration: string;
  duration_hours: number;
  priority: "Critical" | "High" | "Medium" | "Routine";
  priority_color: string;
  urgency_score: number;
  technician: string;
  estimated_cost: number;
  health_score: number;
  failure_risk: number;
  rul_days: number;
  root_causes: string[];
  recommendation: string;
  reasoning: string[];
  status: string;
}

interface AISummary {
  this_week_count: number;
  critical_count: number;
  high_count: number;
  total_events: number;
  total_cost_estimate: number;
  expected_savings: number;
  downtime_prevented: number;
  insight: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const MONTHS = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"];
const DAYS   = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

function priorityBg(p: string) {
  return { Critical: "rgba(239,68,68,0.15)", High: "rgba(249,115,22,0.15)",
           Medium: "rgba(251,191,36,0.12)", Routine: "rgba(52,211,153,0.12)" }[p] ?? "rgba(255,255,255,0.05)";
}
function priorityBorder(p: string) {
  return { Critical: "rgba(239,68,68,0.5)", High: "rgba(249,115,22,0.5)",
           Medium: "rgba(251,191,36,0.4)", Routine: "rgba(52,211,153,0.4)" }[p] ?? "rgba(255,255,255,0.1)";
}
function priorityDot(p: string) {
  return { Critical: "#EF4444", High: "#F97316", Medium: "#FBBF24", Routine: "#34D399" }[p] ?? "#94A3B8";
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function EventModal({ event, onClose }: { event: CalendarEvent; onClose: () => void }) {
  const navigate = useNavigate();
  const dot = priorityDot(event.priority);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 1000, backdropFilter: "blur(4px)",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: "#0F172A", border: `1px solid ${priorityBorder(event.priority)}`,
          borderRadius: 16, padding: 28, width: 420, maxWidth: "90vw",
          boxShadow: `0 0 40px ${dot}22`,
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span style={{ width: 10, height: 10, borderRadius: "50%", background: dot, boxShadow: `0 0 8px ${dot}`, display: "inline-block" }} />
              <span style={{ fontSize: 11, color: dot, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
                {event.priority}
              </span>
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 2 }}>Vehicle {event.vehicle_id}</h2>
            <p style={{ fontSize: 14, color: "#94A3B8" }}>{event.task}</p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#475569", fontSize: 20, cursor: "pointer" }}>✕</button>
        </div>

        {/* Schedule info */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 18 }}>
          {[
            { icon: "📅", label: "Date",       val: event.date },
            { icon: "🕐", label: "Time",       val: event.time },
            { icon: "⏱",  label: "Duration",   val: event.duration },
            { icon: "👨‍🔧", label: "Technician", val: event.technician },
            { icon: "💰", label: "Est. Cost",  val: `₹${event.estimated_cost.toLocaleString("en-IN")}` },
            { icon: "🎯", label: "Urgency",    val: `${event.urgency_score}/100` },
          ].map(r => (
            <div key={r.label} style={{ background: "rgba(255,255,255,0.03)", borderRadius: 8, padding: "10px 12px" }}>
              <div style={{ fontSize: 11, color: "#475569", marginBottom: 3 }}>{r.icon} {r.label}</div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{r.val}</div>
            </div>
          ))}
        </div>

        {/* Health metrics */}
        <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
          {[
            { label: "Health",       val: `${event.health_score}%`,  color: event.health_score > 60 ? "#34D399" : event.health_score > 35 ? "#FBBF24" : "#EF4444" },
            { label: "Failure Risk", val: `${event.failure_risk}%`,  color: event.failure_risk > 70 ? "#EF4444" : event.failure_risk > 40 ? "#FBBF24" : "#34D399" },
            { label: "RUL",          val: `${event.rul_days}d`,      color: event.rul_days < 7 ? "#EF4444" : event.rul_days < 20 ? "#FBBF24" : "#34D399" },
          ].map(m => (
            <div key={m.label} style={{ flex: 1, textAlign: "center", background: "rgba(255,255,255,0.03)", borderRadius: 8, padding: "8px 4px" }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: m.color }}>{m.val}</div>
              <div style={{ fontSize: 10, color: "#475569" }}>{m.label}</div>
            </div>
          ))}
        </div>

        {/* Root causes */}
        {event.root_causes.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: "#475569", marginBottom: 6 }}>🔍 Root Causes</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {event.root_causes.map(c => (
                <span key={c} style={{ fontSize: 11, padding: "3px 10px", borderRadius: 20, background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.25)", color: "#FCA5A5" }}>
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* AI reasoning */}
        {event.reasoning.length > 0 && (
          <div style={{ marginBottom: 18 }}>
            <div style={{ fontSize: 11, color: "#475569", marginBottom: 6 }}>🧠 AI Reasoning</div>
            {event.reasoning.map((r, i) => (
              <div key={i} style={{ fontSize: 12, color: "#94A3B8", padding: "4px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                • {r}
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={() => navigate(`/vehicle/${event.vehicle_id}`)}
            style={{
              flex: 1, padding: "10px 0", borderRadius: 8, border: "none", cursor: "pointer",
              background: "linear-gradient(135deg,#38BDF8,#6366F1)", color: "#fff", fontWeight: 700, fontSize: 13,
            }}
          >
            Open Digital Twin →
          </button>
          <button
            onClick={() => navigate(`/workorder/${event.vehicle_id}`)}
            style={{
              flex: 1, padding: "10px 0", borderRadius: 8, border: "none", cursor: "pointer",
              background: "rgba(52,211,153,0.15)", border: "1px solid rgba(52,211,153,0.3)",
              color: "#34D399", fontWeight: 700, fontSize: 13,
            }}
          >
            🗒 Work Order
          </button>
          <button
            onClick={onClose}
            style={{
              padding: "10px 16px", borderRadius: 8, cursor: "pointer",
              background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
              color: "#94A3B8", fontSize: 13,
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function MaintenanceCalendar() {
  const [events,    setEvents]    = useState<CalendarEvent[]>(() => getCached<CalendarEvent[]>("cal_events") ?? []);
  const [summary,   setSummary]   = useState<AISummary | null>(() => getCached<AISummary>("cal_summary"));
  const [loading,   setLoading]   = useState(() => !getCached("cal_events"));
  const [selected,  setSelected]  = useState<CalendarEvent | null>(null);
  const [viewMonth, setViewMonth] = useState(() => {
    const d = new Date(); return { year: d.getFullYear(), month: d.getMonth() };
  });
  const [filterPriority, setFilterPriority] = useState<string>("All");

  useEffect(() => {
    if (getCached("cal_events")) { setLoading(false); return; }
    api.get("/calendar").then(r => {
      setCached("cal_events",  r.data.events);
      setCached("cal_summary", r.data.ai_summary);
      setEvents(r.data.events);
      setSummary(r.data.ai_summary);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // ── Calendar grid ──────────────────────────────────────────────────────────
  const { year, month } = viewMonth;
  const firstDay  = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const eventsByDate = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {};
    events.forEach(e => {
      if (filterPriority !== "All" && e.priority !== filterPriority) return;
      (map[e.date] ??= []).push(e);
    });
    return map;
  }, [events, filterPriority]);

  const todayStr = new Date().toISOString().split("T")[0];

  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  // ── List view (upcoming) ───────────────────────────────────────────────────
  const upcomingEvents = useMemo(() =>
    [...events]
      .filter(e => filterPriority === "All" || e.priority === filterPriority)
      .sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time))
      .slice(0, 15),
    [events, filterPriority]
  );

  const bg = "#05070A";

  return (
    <div style={{ background: bg, minHeight: "100vh", paddingTop: 56 }}>
      <Navbar connected={false} />

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 32px 64px" }}>

        {/* ── HERO ──────────────────────────────────────────────────────────── */}
        <div style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <Link to="/" style={{ color: "#475569", fontSize: 13, textDecoration: "none" }}>← Dashboard</Link>
            <span style={{ color: "#1E293B" }}>/</span>
            <span style={{ color: "#38BDF8", fontSize: 13 }}>Maintenance Calendar</span>
          </div>
          <h1 style={{
            fontSize: "clamp(24px,3vw,40px)", fontWeight: 900, letterSpacing: "-1.5px",
            background: "linear-gradient(135deg,#F1F5F9 30%,#38BDF8 70%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            🗓 AI Predictive Maintenance Calendar
          </h1>
          <p style={{ color: "#475569", fontSize: 14, marginTop: 6 }}>
            Auto-generated schedule from Health · Failure · RUL · Fleet Priority models
          </p>
        </div>

        {/* ── AI SUMMARY BANNER ─────────────────────────────────────────────── */}
        {summary && (
          <div style={{
            marginBottom: 28, padding: "20px 24px", borderRadius: 14,
            background: "linear-gradient(135deg,rgba(56,189,248,0.08),rgba(99,102,241,0.08))",
            border: "1px solid rgba(56,189,248,0.2)",
          }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={{ fontSize: 11, color: "#38BDF8", fontWeight: 700, letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>
                  🧠 AI Recommendation
                </div>
                <p style={{ fontSize: 14, color: "#CBD5E1", lineHeight: 1.6 }}>{summary.insight}</p>
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                {[
                  { label: "This Week",        val: summary.this_week_count,                                    color: "#38BDF8", suffix: " jobs" },
                  { label: "Critical Today",   val: summary.critical_count,                                     color: "#EF4444", suffix: "" },
                  { label: "Expected Savings", val: `₹${(summary.expected_savings/100000).toFixed(1)}L`,        color: "#34D399", suffix: "" },
                  { label: "Downtime Reduced", val: `${summary.downtime_prevented}h`,                           color: "#A78BFA", suffix: "" },
                ].map(s => (
                  <div key={s.label} style={{
                    textAlign: "center", padding: "12px 18px", borderRadius: 10,
                    background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
                    minWidth: 90,
                  }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: s.color }}>{s.val}{s.suffix}</div>
                    <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── FILTER + NAV ──────────────────────────────────────────────────── */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
          {/* Priority filter */}
          <div style={{ display: "flex", gap: 8 }}>
            {["All", "Critical", "High", "Medium", "Routine"].map(p => (
              <button
                key={p}
                onClick={() => setFilterPriority(p)}
                style={{
                  padding: "6px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600, cursor: "pointer",
                  border: `1px solid ${filterPriority === p ? priorityDot(p) : "rgba(255,255,255,0.1)"}`,
                  background: filterPriority === p ? priorityBg(p) : "transparent",
                  color: filterPriority === p ? priorityDot(p) : "#475569",
                  transition: "all 0.15s",
                }}
              >
                {p === "All" ? "All" : (
                  <><span style={{ width: 6, height: 6, borderRadius: "50%", background: priorityDot(p), display: "inline-block", marginRight: 5 }} />{p}</>
                )}
              </button>
            ))}
          </div>

          {/* Month nav */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button
              onClick={() => setViewMonth(v => {
                const d = new Date(v.year, v.month - 1); return { year: d.getFullYear(), month: d.getMonth() };
              })}
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#94A3B8", borderRadius: 8, padding: "6px 12px", cursor: "pointer", fontSize: 14 }}
            >‹</button>
            <span style={{ fontWeight: 700, fontSize: 15, minWidth: 140, textAlign: "center" }}>
              {MONTHS[month]} {year}
            </span>
            <button
              onClick={() => setViewMonth(v => {
                const d = new Date(v.year, v.month + 1); return { year: d.getFullYear(), month: d.getMonth() };
              })}
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#94A3B8", borderRadius: 8, padding: "6px 12px", cursor: "pointer", fontSize: 14 }}
            >›</button>
          </div>
        </div>

        {/* ── MAIN LAYOUT: Calendar + Sidebar ───────────────────────────────── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20, alignItems: "start" }}>

          {/* ── CALENDAR GRID ─────────────────────────────────────────────── */}
          <div className="glass" style={{ padding: 20 }}>
            {/* Day headers */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 4, marginBottom: 8 }}>
              {DAYS.map(d => (
                <div key={d} style={{ textAlign: "center", fontSize: 11, color: "#334155", fontWeight: 700, padding: "6px 0" }}>{d}</div>
              ))}
            </div>

            {loading ? (
              <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center", color: "#334155" }}>
                Generating AI schedule…
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 4 }}>
                {cells.map((day, idx) => {
                  if (!day) return <div key={`empty-${idx}`} />;
                  const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
                  const dayEvents = eventsByDate[dateStr] ?? [];
                  const isToday   = dateStr === todayStr;
                  const hasCritical = dayEvents.some(e => e.priority === "Critical");
                  const hasHigh     = dayEvents.some(e => e.priority === "High");
                  const cellColor   = hasCritical ? "#EF4444" : hasHigh ? "#F97316" : dayEvents.length ? "#FBBF24" : "transparent";

                  return (
                    <div
                      key={dateStr}
                      style={{
                        minHeight: 80, borderRadius: 8, padding: "6px 6px 4px",
                        background: isToday ? "rgba(56,189,248,0.08)" : dayEvents.length ? "rgba(255,255,255,0.02)" : "transparent",
                        border: isToday ? "1px solid rgba(56,189,248,0.4)" : dayEvents.length ? `1px solid ${cellColor}33` : "1px solid rgba(255,255,255,0.04)",
                        transition: "all 0.15s",
                        cursor: dayEvents.length ? "pointer" : "default",
                      }}
                    >
                      {/* Day number */}
                      <div style={{
                        fontSize: 12, fontWeight: isToday ? 800 : 500,
                        color: isToday ? "#38BDF8" : "#64748B",
                        marginBottom: 4,
                      }}>
                        {day}
                        {isToday && <span style={{ fontSize: 9, marginLeft: 3, color: "#38BDF8" }}>TODAY</span>}
                      </div>

                      {/* Event chips */}
                      {dayEvents.slice(0, 3).map((e, i) => (
                        <div
                          key={i}
                          onClick={() => setSelected(e)}
                          style={{
                            fontSize: 10, padding: "2px 5px", borderRadius: 4, marginBottom: 2,
                            background: priorityBg(e.priority),
                            border: `1px solid ${priorityBorder(e.priority)}`,
                            color: priorityDot(e.priority),
                            overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis",
                            cursor: "pointer",
                          }}
                          title={`V${e.vehicle_id} — ${e.task}`}
                        >
                          <span style={{ width: 5, height: 5, borderRadius: "50%", background: priorityDot(e.priority), display: "inline-block", marginRight: 3 }} />
                          V{e.vehicle_id}
                        </div>
                      ))}
                      {dayEvents.length > 3 && (
                        <div style={{ fontSize: 9, color: "#475569", paddingLeft: 2 }}>+{dayEvents.length - 3} more</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Legend */}
            <div style={{ display: "flex", gap: 16, marginTop: 16, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.06)", flexWrap: "wrap" }}>
              {[["Critical","#EF4444"],["High","#F97316"],["Medium","#FBBF24"],["Routine","#34D399"]].map(([l,c]) => (
                <span key={l} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: "#475569" }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: c, display: "inline-block" }} /> {l}
                </span>
              ))}
            </div>
          </div>

          {/* ── SIDEBAR: Upcoming Events ───────────────────────────────────── */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="glass" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 14, color: "#F1F5F9" }}>
                📋 Upcoming Schedule
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 520, overflowY: "auto" }}>
                {upcomingEvents.map((e, i) => (
                  <div
                    key={i}
                    onClick={() => setSelected(e)}
                    style={{
                      padding: "10px 12px", borderRadius: 10, cursor: "pointer",
                      background: priorityBg(e.priority),
                      border: `1px solid ${priorityBorder(e.priority)}`,
                      transition: "all 0.15s",
                    }}
                    onMouseEnter={el => (el.currentTarget.style.transform = "translateX(3px)")}
                    onMouseLeave={el => (el.currentTarget.style.transform = "translateX(0)")}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 700 }}>Vehicle {e.vehicle_id}</span>
                      <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: 10, background: `${priorityDot(e.priority)}22`, color: priorityDot(e.priority), fontWeight: 700 }}>
                        {e.priority}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 3 }}>{e.task}</div>
                    <div style={{ display: "flex", gap: 10, fontSize: 11, color: "#475569" }}>
                      <span>📅 {e.date}</span>
                      <span>🕐 {e.time}</span>
                      <span>⏱ {e.duration}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#475569", marginTop: 3 }}>👨‍🔧 {e.technician}</div>
                  </div>
                ))}
                {upcomingEvents.length === 0 && (
                  <div style={{ color: "#334155", fontSize: 13, textAlign: "center", padding: "20px 0" }}>
                    No events for selected filter
                  </div>
                )}
              </div>
            </div>

            {/* Priority breakdown */}
            {summary && (
              <div className="glass" style={{ padding: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 14 }}>📊 Priority Breakdown</h3>
                {[
                  { label: "Critical", count: summary.critical_count,                                                                  color: "#EF4444" },
                  { label: "High",     count: summary.high_count,                                                                      color: "#F97316" },
                  { label: "Medium",   count: summary.total_events - summary.critical_count - summary.high_count - Math.max(0, summary.total_events - summary.critical_count - summary.high_count - events.filter(e=>e.priority==="Routine").length), color: "#FBBF24" },
                  { label: "Routine",  count: events.filter(e => e.priority === "Routine").length,                                     color: "#34D399" },
                ].map(row => (
                  <div key={row.label} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                      <span style={{ color: "#64748B" }}>{row.label}</span>
                      <span style={{ color: row.color, fontWeight: 700 }}>{row.count}</span>
                    </div>
                    <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 4 }}>
                      <div style={{
                        width: `${summary.total_events ? (row.count / summary.total_events) * 100 : 0}%`,
                        height: "100%", background: row.color, borderRadius: 4, transition: "width 1s",
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── EVENT MODAL ─────────────────────────────────────────────────────── */}
      {selected && <EventModal event={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

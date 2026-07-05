import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api";
import Navbar from "../components/Navbar";
import { getCached, setCached } from "../store/fleetStore";

// ── Types ─────────────────────────────────────────────────────────────────────
interface Technician {
  id: number;
  name: string;
  skills: string[];
  experience: number;
  rating: number;
  available: boolean;
  workload: number;
  current_jobs: string[];
  shift: string;
  avatar: string;
  phone: string;
  status: "Available" | "Working" | "Off Duty";
}

interface Assignment {
  vehicle_id: number;
  task: string;
  priority: string;
  technician: string;
  technician_id: number;
  score: number;
  estimated_start: string;
  estimated_finish: string;
  duration_hours: number;
}

interface FleetAssignment {
  assignments: Assignment[];
  summary: {
    total_technicians: number;
    available: number;
    working: number;
    off_duty: number;
    total_assignments: number;
    avg_repair_hours: number;
    completion_pct: number;
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const PRIORITY_COLOR: Record<string, string> = {
  Critical: "#EF4444", High: "#F97316", Medium: "#FBBF24", Routine: "#34D399",
};
const STATUS_COLOR: Record<string, string> = {
  Available: "#34D399", Working: "#FBBF24", "Off Duty": "#475569",
};
const STATUS_BG: Record<string, string> = {
  Available: "rgba(52,211,153,0.1)", Working: "rgba(251,191,36,0.1)", "Off Duty": "rgba(71,85,105,0.1)",
};
const STATUS_BORDER: Record<string, string> = {
  Available: "rgba(52,211,153,0.3)", Working: "rgba(251,191,36,0.3)", "Off Duty": "rgba(71,85,105,0.3)",
};

function pc(p: string) { return PRIORITY_COLOR[p] ?? "#94A3B8"; }

function StarRating({ rating }: { rating: number }) {
  return (
    <span style={{ fontSize: 11, color: "#FBBF24" }}>
      {"★".repeat(Math.floor(rating))}{"☆".repeat(5 - Math.floor(rating))}
      <span style={{ color: "#64748B", marginLeft: 4 }}>{rating}</span>
    </span>
  );
}

function SkillBadge({ skill }: { skill: string }) {
  const colors: Record<string, string> = {
    Battery: "#38BDF8", Electrical: "#38BDF8", "HV Systems": "#38BDF8",
    Cooling: "#34D399", Thermal: "#34D399",
    Motor: "#A78BFA", Engine: "#A78BFA", Powertrain: "#A78BFA",
    Transmission: "#F97316", Drivetrain: "#F97316",
    Brake: "#EF4444", Suspension: "#EF4444",
    General: "#64748B", Diagnostics: "#64748B",
  };
  const c = colors[skill] ?? "#64748B";
  return (
    <span style={{
      fontSize: 10, padding: "2px 7px", borderRadius: 10,
      background: `${c}18`, border: `1px solid ${c}40`, color: c, fontWeight: 600,
    }}>
      {skill}
    </span>
  );
}

// ── Technician Card ───────────────────────────────────────────────────────────
function TechCard({ tech, assignments }: { tech: Technician; assignments: Assignment[] }) {
  const myJobs = assignments.filter(a => a.technician === tech.name);
  const sc     = STATUS_COLOR[tech.status];

  return (
    <div style={{
      padding: "14px 16px", borderRadius: 12,
      background: STATUS_BG[tech.status],
      border: `1px solid ${STATUS_BORDER[tech.status]}`,
      transition: "all 0.2s",
    }}
      onMouseEnter={e => (e.currentTarget.style.transform = "translateY(-2px)")}
      onMouseLeave={e => (e.currentTarget.style.transform = "translateY(0)")}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <div style={{
          width: 38, height: 38, borderRadius: "50%", flexShrink: 0,
          background: `linear-gradient(135deg,${sc}33,${sc}11)`,
          border: `2px solid ${sc}55`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 12, fontWeight: 800, color: sc,
        }}>
          {tech.avatar.slice(0, 2)}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#F1F5F9", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {tech.name}
          </div>
          <StarRating rating={tech.rating} />
        </div>
        <div style={{
          fontSize: 10, padding: "2px 8px", borderRadius: 10,
          background: `${sc}18`, border: `1px solid ${sc}44`, color: sc, fontWeight: 700,
        }}>
          {tech.status}
        </div>
      </div>

      {/* Skills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
        {tech.skills.slice(0, 3).map(s => <SkillBadge key={s} skill={s} />)}
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 12, fontSize: 11, color: "#475569", marginBottom: 8 }}>
        <span>🎓 {tech.experience}y exp</span>
        <span>📋 {tech.workload} jobs</span>
        <span>🕐 {tech.shift}</span>
      </div>

      {/* Assigned vehicles */}
      {myJobs.length > 0 && (
        <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 8 }}>
          {myJobs.slice(0, 2).map(j => (
            <div key={j.vehicle_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
              <span style={{ fontSize: 11, color: "#94A3B8" }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: pc(j.priority), display: "inline-block", marginRight: 5 }} />
                V{j.vehicle_id} — {j.task.split(" ")[0]}
              </span>
              <span style={{ fontSize: 10, color: "#475569" }}>{j.estimated_start}–{j.estimated_finish}</span>
            </div>
          ))}
          {myJobs.length > 2 && (
            <div style={{ fontSize: 10, color: "#334155" }}>+{myJobs.length - 2} more</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Assignment Row ────────────────────────────────────────────────────────────
function AssignmentRow({ a, idx }: { a: Assignment; idx: number }) {
  const navigate = useNavigate();
  const col = pc(a.priority);
  return (
    <div
      onClick={() => navigate(`/workorder/${a.vehicle_id}`)}
      style={{
        display: "grid", gridTemplateColumns: "32px 80px 1fr 120px 100px 90px 90px",
        alignItems: "center", gap: 12, padding: "10px 14px", borderRadius: 10,
        background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)",
        cursor: "pointer", transition: "all 0.15s", fontSize: 13,
      }}
      onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
      onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.02)")}
    >
      <span style={{ color: "#334155", fontWeight: 700, fontSize: 11 }}>#{idx + 1}</span>
      <span style={{ fontWeight: 700, color: "#38BDF8" }}>V{a.vehicle_id}</span>
      <span style={{ color: "#94A3B8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.task}</span>
      <span style={{ fontWeight: 600, color: "#F1F5F9" }}>{a.technician}</span>
      <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 10, background: `${col}18`, border: `1px solid ${col}44`, color: col, fontWeight: 700, textAlign: "center" }}>
        {a.priority}
      </span>
      <span style={{ fontSize: 11, color: "#64748B" }}>{a.estimated_start} – {a.estimated_finish}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <div style={{ flex: 1, height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
          <div style={{ width: `${a.score}%`, height: "100%", background: a.score >= 80 ? "#34D399" : "#FBBF24", borderRadius: 2 }} />
        </div>
        <span style={{ fontSize: 10, color: "#475569", minWidth: 28 }}>{a.score}</span>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function TechnicianDashboard() {
  const [techs,      setTechs]      = useState<Technician[]>(() => getCached<Technician[]>("techs") ?? []);
  const [fleetData,  setFleetData]  = useState<FleetAssignment | null>(() => getCached<FleetAssignment>("tech_fleet"));
  const [loading,    setLoading]    = useState(() => !getCached("techs"));
  const [filterStatus, setFilterStatus] = useState<string>("All");
  const [searchQuery,  setSearchQuery]  = useState("");
  const [activeTab,    setActiveTab]    = useState<"kanban" | "assignments">("kanban");

  useEffect(() => {
    if (getCached("techs")) { setLoading(false); return; }
    Promise.all([
      api.get("/technicians"),
      api.get("/assignments/fleet"),
    ]).then(([t, f]) => {
      const techList = Array.isArray(t.data) ? t.data : (t.data.technicians ?? []);
      setCached("techs",      techList);
      setCached("tech_fleet", f.data);
      setTechs(techList);
      setFleetData(f.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const assignments = fleetData?.assignments ?? [];
  const summary     = fleetData?.summary;

  // Kanban columns
  const kanbanCols = useMemo(() => ({
    Available: techs.filter(t => t.status === "Available"),
    Working:   techs.filter(t => t.status === "Working"),
    "Off Duty": techs.filter(t => t.status === "Off Duty"),
  }), [techs]);

  // Filtered techs for search
  const filteredTechs = useMemo(() =>
    techs.filter(t =>
      (filterStatus === "All" || t.status === filterStatus) &&
      (searchQuery === "" || t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
       t.skills.some(s => s.toLowerCase().includes(searchQuery.toLowerCase())))
    ), [techs, filterStatus, searchQuery]);

  const bg = "#05070A";

  return (
    <div style={{ background: bg, minHeight: "100vh", paddingTop: 56 }}>
      <Navbar connected={false} />

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 32px 80px" }}>

        {/* ── Breadcrumb + Hero ──────────────────────────────────────────────── */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <Link to="/" style={{ color: "#475569", fontSize: 13, textDecoration: "none" }}>← Dashboard</Link>
            <span style={{ color: "#1E293B" }}>/</span>
            <span style={{ color: "#38BDF8", fontSize: 13 }}>Technician Assignment</span>
          </div>
          <h1 style={{
            fontSize: "clamp(22px,3vw,40px)", fontWeight: 900, letterSpacing: "-1.5px",
            background: "linear-gradient(135deg,#F1F5F9 30%,#34D399 70%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            👨‍🔧 AI Technician Assignment Engine
          </h1>
          <p style={{ color: "#475569", fontSize: 14, marginTop: 6 }}>
            Skill matching · Workload balancing · Priority-aware assignment
          </p>
        </div>

        {/* ── AI Insights Banner ─────────────────────────────────────────────── */}
        {summary && (
          <div style={{
            marginBottom: 28, padding: "20px 24px", borderRadius: 14,
            background: "linear-gradient(135deg,rgba(52,211,153,0.07),rgba(56,189,248,0.07))",
            border: "1px solid rgba(52,211,153,0.2)",
          }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 20, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <div style={{ fontSize: 11, color: "#34D399", fontWeight: 700, letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>
                  🧠 Today's Workforce Intelligence
                </div>
                <p style={{ fontSize: 14, color: "#CBD5E1", lineHeight: 1.6 }}>
                  {summary.available} technicians available out of {summary.total_technicians}.{" "}
                  {summary.total_assignments} vehicles assigned. Average repair time {summary.avg_repair_hours}h.{" "}
                  Expected completion rate {summary.completion_pct}%.
                </p>
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                {[
                  { label: "Total Technicians", val: summary.total_technicians, color: "#38BDF8" },
                  { label: "Available",          val: summary.available,         color: "#34D399" },
                  { label: "Working",            val: summary.working,           color: "#FBBF24" },
                  { label: "Avg Repair Time",    val: `${summary.avg_repair_hours}h`, color: "#A78BFA" },
                  { label: "Completion Rate",    val: `${summary.completion_pct}%`,  color: "#34D399" },
                ].map(s => (
                  <div key={s.label} style={{
                    textAlign: "center", padding: "12px 16px", borderRadius: 10,
                    background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", minWidth: 80,
                  }}>
                    <div style={{ fontSize: 20, fontWeight: 800, color: s.color }}>{s.val}</div>
                    <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── Tab nav ───────────────────────────────────────────────────────── */}
        <div style={{ display: "flex", gap: 4, marginBottom: 24, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: 4, width: "fit-content" }}>
          {([
            { id: "kanban",      label: "🗂 Kanban Board" },
            { id: "assignments", label: "📋 All Assignments" },
          ] as const).map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: "8px 20px", borderRadius: 9, cursor: "pointer", fontSize: 13,
                border: activeTab === tab.id ? "1px solid rgba(56,189,248,0.25)" : "1px solid transparent",
                background: activeTab === tab.id ? "rgba(56,189,248,0.12)" : "transparent",
                color: activeTab === tab.id ? "#38BDF8" : "#475569",
                fontWeight: activeTab === tab.id ? 700 : 400, transition: "all 0.15s",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── KANBAN BOARD ──────────────────────────────────────────────────── */}
        {activeTab === "kanban" && (
          <>
            {loading ? (
              <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center", color: "#334155" }}>
                <div style={{ textAlign: "center" }}>
                  <div style={{ width: 32, height: 32, border: "3px solid rgba(52,211,153,0.3)", borderTop: "3px solid #34D399", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 10px" }} />
                  Loading technicians…
                  <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                </div>
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20 }}>
                {(["Available", "Working", "Off Duty"] as const).map(col => {
                  const colTechs = kanbanCols[col];
                  const sc = STATUS_COLOR[col];
                  return (
                    <div key={col}>
                      {/* Column header */}
                      <div style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        padding: "10px 16px", borderRadius: "10px 10px 0 0",
                        background: STATUS_BG[col], border: `1px solid ${STATUS_BORDER[col]}`,
                        borderBottom: "none", marginBottom: 0,
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ width: 8, height: 8, borderRadius: "50%", background: sc, boxShadow: `0 0 8px ${sc}`, display: "inline-block" }} />
                          <span style={{ fontSize: 13, fontWeight: 700, color: sc }}>{col}</span>
                        </div>
                        <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 10, background: `${sc}22`, color: sc, fontWeight: 700 }}>
                          {colTechs.length}
                        </span>
                      </div>

                      {/* Cards */}
                      <div style={{
                        padding: 12, borderRadius: "0 0 10px 10px",
                        background: "rgba(255,255,255,0.01)",
                        border: `1px solid ${STATUS_BORDER[col]}`,
                        borderTop: "none", minHeight: 200,
                        display: "flex", flexDirection: "column", gap: 10,
                      }}>
                        {colTechs.length === 0 ? (
                          <div style={{ color: "#1E293B", fontSize: 12, textAlign: "center", padding: "20px 0" }}>
                            No technicians
                          </div>
                        ) : (
                          colTechs.map(t => (
                            <TechCard key={t.id} tech={t} assignments={assignments} />
                          ))
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* ── ASSIGNMENTS TABLE ─────────────────────────────────────────────── */}
        {activeTab === "assignments" && (
          <div className="glass" style={{ padding: 24 }}>
            {/* Table header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 700 }}>📋 Fleet Assignments</h3>
                <p style={{ fontSize: 12, color: "#475569", marginTop: 2 }}>
                  AI-assigned — sorted by urgency · Click any row to open work order
                </p>
              </div>
              {/* Filter pills */}
              <div style={{ display: "flex", gap: 8 }}>
                {["All", "Critical", "High", "Medium", "Routine"].map(p => (
                  <button
                    key={p}
                    onClick={() => setFilterStatus(p)}
                    style={{
                      padding: "5px 12px", borderRadius: 20, fontSize: 11, fontWeight: 600, cursor: "pointer",
                      border: `1px solid ${filterStatus === p ? pc(p) : "rgba(255,255,255,0.1)"}`,
                      background: filterStatus === p ? `${pc(p)}18` : "transparent",
                      color: filterStatus === p ? pc(p) : "#475569", transition: "all 0.15s",
                    }}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {/* Column headers */}
            <div style={{
              display: "grid", gridTemplateColumns: "32px 80px 1fr 120px 100px 90px 90px",
              gap: 12, padding: "6px 14px", marginBottom: 6,
              fontSize: 10, color: "#334155", fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5,
            }}>
              <span>#</span><span>Vehicle</span><span>Task</span>
              <span>Technician</span><span>Priority</span><span>Time</span><span>AI Score</span>
            </div>

            {/* Rows */}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {assignments
                .filter(a => filterStatus === "All" || a.priority === filterStatus)
                .map((a, i) => <AssignmentRow key={a.vehicle_id} a={a} idx={i} />)
              }
              {assignments.filter(a => filterStatus === "All" || a.priority === filterStatus).length === 0 && (
                <div style={{ color: "#334155", textAlign: "center", padding: "32px 0", fontSize: 13 }}>
                  No assignments for selected filter
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Skill Coverage Matrix ──────────────────────────────────────────── */}
        {!loading && (
          <div className="glass" style={{ padding: 24, marginTop: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16, color: "#38BDF8" }}>
              🎯 Skill Coverage Matrix
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(140px,1fr))", gap: 10 }}>
              {["Battery", "Electrical", "Cooling", "Motor", "Transmission", "Brake", "Diagnostics", "General"].map(skill => {
                const experts = techs.filter(t => t.skills.includes(skill));
                const available = experts.filter(t => t.available);
                const pct = experts.length ? Math.round((available.length / experts.length) * 100) : 0;
                const colors: Record<string, string> = {
                  Battery: "#38BDF8", Electrical: "#38BDF8", Cooling: "#34D399",
                  Motor: "#A78BFA", Transmission: "#F97316", Brake: "#EF4444",
                  Diagnostics: "#64748B", General: "#64748B",
                };
                const c = colors[skill] ?? "#64748B";
                return (
                  <div key={skill} style={{ padding: "12px 14px", borderRadius: 10, background: `${c}08`, border: `1px solid ${c}22` }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: c, marginBottom: 6 }}>{skill}</div>
                    <div style={{ fontSize: 11, color: "#475569", marginBottom: 6 }}>
                      {available.length}/{experts.length} available
                    </div>
                    <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
                      <div style={{ width: `${pct}%`, height: "100%", background: c, borderRadius: 2, transition: "width 1s" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../services/api";

// ── Types ─────────────────────────────────────────────────────────────────────
interface WorkOrder {
  work_order_id: string;
  generated_at: string;
  vehicle_id: number;
  vehicle_model: string;
  priority: string;
  status: string;
  scheduled_date: string;
  task: string;
  duration: string;
  duration_hours: number;
  technician: string;
  technician_skill: string;
  parts: string[];
  tools: string[];
  checklist: string[];
  instructions: { before: string[]; during: string[]; after: string[] };
  health_score: number;
  failure_risk: number;
  rul_days: number;
  root_causes: string[];
  estimated_risk: string;
  confidence_score: number;
  estimated_cost: number;
  failure_cost: number;
  potential_savings: number;
  ai_summary: string;
  reasoning: string[];
  qr_data: string;
}

// ── Constants ─────────────────────────────────────────────────────────────────
const PROGRESS_STAGES = [
  { id: "Created",     icon: "📋", label: "Created" },
  { id: "Assigned",    icon: "👨‍🔧", label: "Assigned" },
  { id: "In Progress", icon: "🔧", label: "In Progress" },
  { id: "Testing",     icon: "🧪", label: "Testing" },
  { id: "Completed",   icon: "✅", label: "Completed" },
];

const PRIORITY_COLOR: Record<string, string> = {
  Critical: "#EF4444", High: "#F97316", Medium: "#FBBF24", Routine: "#34D399",
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function pc(p: string) { return PRIORITY_COLOR[p] ?? "#94A3B8"; }
function healthColor(h: number) { return h >= 75 ? "#34D399" : h >= 45 ? "#FBBF24" : "#EF4444"; }

// ── Sub-components ────────────────────────────────────────────────────────────
function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="glass" style={{ padding: 24 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, color: "#38BDF8", marginBottom: 16 }}>{title}</h3>
      {children}
    </div>
  );
}

function KVRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)", fontSize: 13 }}>
      <span style={{ color: "#64748B" }}>{label}</span>
      <span style={{ fontWeight: 700, color: color ?? "#F1F5F9" }}>{value}</span>
    </div>
  );
}

function CheckItem({ text, checked, onToggle }: { text: string; checked: boolean; onToggle: () => void }) {
  return (
    <div
      onClick={onToggle}
      style={{
        display: "flex", alignItems: "flex-start", gap: 10, padding: "8px 10px",
        borderRadius: 8, cursor: "pointer", transition: "all 0.15s",
        background: checked ? "rgba(52,211,153,0.06)" : "rgba(255,255,255,0.02)",
        border: `1px solid ${checked ? "rgba(52,211,153,0.25)" : "rgba(255,255,255,0.06)"}`,
        marginBottom: 6,
      }}
    >
      <div style={{
        width: 18, height: 18, borderRadius: 4, flexShrink: 0, marginTop: 1,
        background: checked ? "#34D399" : "transparent",
        border: `2px solid ${checked ? "#34D399" : "#334155"}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        transition: "all 0.15s",
      }}>
        {checked && <span style={{ fontSize: 11, color: "#0F172A", fontWeight: 900 }}>✓</span>}
      </div>
      <span style={{ fontSize: 13, color: checked ? "#94A3B8" : "#CBD5E1", textDecoration: checked ? "line-through" : "none", lineHeight: 1.4 }}>
        {text}
      </span>
    </div>
  );
}

// ── Progress Timeline ─────────────────────────────────────────────────────────
function ProgressTimeline({ currentStatus, onChange }: { currentStatus: string; onChange: (s: string) => void }) {
  const currentIdx = PROGRESS_STAGES.findIndex(s => s.id === currentStatus);

  return (
    <div style={{ padding: "20px 0" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", position: "relative" }}>
        {/* Track */}
        <div style={{ position: "absolute", top: 20, left: "5%", right: "5%", height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2, zIndex: 0 }}>
          <div style={{
            height: "100%", borderRadius: 2,
            background: "linear-gradient(90deg,#34D399,#38BDF8)",
            width: `${currentIdx === 0 ? 0 : (currentIdx / (PROGRESS_STAGES.length - 1)) * 100}%`,
            transition: "width 0.6s ease",
          }} />
        </div>

        {PROGRESS_STAGES.map((stage, idx) => {
          const done    = idx < currentIdx;
          const active  = idx === currentIdx;
          const pending = idx > currentIdx;
          const color   = done ? "#34D399" : active ? "#38BDF8" : "#1E293B";
          const border  = done ? "#34D399" : active ? "#38BDF8" : "#334155";

          return (
            <div
              key={stage.id}
              onClick={() => onChange(stage.id)}
              style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, zIndex: 1, cursor: "pointer", flex: 1 }}
            >
              <div style={{
                width: 40, height: 40, borderRadius: "50%",
                background: done ? "rgba(52,211,153,0.15)" : active ? "rgba(56,189,248,0.15)" : "rgba(255,255,255,0.03)",
                border: `2px solid ${border}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 16, transition: "all 0.3s",
                boxShadow: active ? `0 0 16px ${color}44` : "none",
              }}>
                {done ? "✓" : stage.icon}
              </div>
              <span style={{ fontSize: 11, fontWeight: active ? 700 : 400, color: pending ? "#334155" : color, textAlign: "center" }}>
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function WorkOrder() {
  const { id }       = useParams();
  const navigate     = useNavigate();
  const [wo, setWo]  = useState<WorkOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus]   = useState("Created");
  const [checked, setChecked] = useState<boolean[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "checklist" | "instructions" | "parts">("overview");

  useEffect(() => {
    api.get(`/workorder/${id}`).then(r => {
      setWo(r.data);
      setStatus(r.data.status);
      setChecked(new Array(r.data.checklist.length).fill(false));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div style={{ minHeight: "100vh", background: "#05070A", display: "flex", alignItems: "center", justifyContent: "center", color: "#475569" }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ width: 36, height: 36, border: "3px solid rgba(56,189,248,0.3)", borderTop: "3px solid #38BDF8", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 12px" }} />
        Generating work order…
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    </div>
  );

  if (!wo) return (
    <div style={{ minHeight: "100vh", background: "#05070A", display: "flex", alignItems: "center", justifyContent: "center", color: "#EF4444" }}>
      Work order not found. <Link to="/" style={{ color: "#38BDF8", marginLeft: 8 }}>← Back</Link>
    </div>
  );

  const checkedCount = checked.filter(Boolean).length;
  const checkPct     = Math.round((checkedCount / wo.checklist.length) * 100);
  const priorityCol  = pc(wo.priority);

  const TABS = [
    { id: "overview",     label: "Overview",     icon: "📊" },
    { id: "checklist",    label: `Checklist (${checkedCount}/${wo.checklist.length})`, icon: "✅" },
    { id: "instructions", label: "Instructions", icon: "📋" },
    { id: "parts",        label: "Parts & Tools", icon: "🔧" },
  ] as const;

  return (
    <div style={{ background: "#05070A", minHeight: "100vh" }}>

      {/* ── Top bar ─────────────────────────────────────────────────────────── */}
      <div style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        background: "rgba(5,7,10,0.92)", backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "0 32px", height: 56,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link to={`/vehicle/${id}`} style={{ color: "#475569", fontSize: 13, textDecoration: "none" }}>← Vehicle {id}</Link>
          <span style={{ color: "#1E293B" }}>|</span>
          <span style={{ fontSize: 13, fontWeight: 700 }}>Work Order</span>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 10, background: `${priorityCol}18`, border: `1px solid ${priorityCol}44`, color: priorityCol, fontWeight: 700 }}>
            {wo.priority}
          </span>
          <span style={{ fontSize: 11, color: "#475569" }}>{wo.work_order_id}</span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <a
            href={`http://127.0.0.1:8000/workorder/${id}/pdf`}
            target="_blank" rel="noreferrer"
            style={{ fontSize: 12, padding: "6px 14px", borderRadius: 8, background: "rgba(56,189,248,0.1)", border: "1px solid rgba(56,189,248,0.3)", color: "#38BDF8", textDecoration: "none", fontWeight: 600 }}
          >
            📄 Download PDF
          </a>
          <button
            onClick={() => navigate(`/vehicle/${id}`)}
            style={{ fontSize: 12, padding: "6px 14px", borderRadius: 8, background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.3)", color: "#A78BFA", cursor: "pointer", fontWeight: 600 }}
          >
            ⚙️ Digital Twin
          </button>
          <button
            onClick={() => navigate("/technicians")}
            style={{ fontSize: 12, padding: "6px 14px", borderRadius: 8, background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.3)", color: "#34D399", cursor: "pointer", fontWeight: 600 }}
          >
            👨🔧 Technicians
          </button>
        </div>
      </div>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "72px 32px 80px" }}>

        {/* ── Hero ──────────────────────────────────────────────────────────── */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
            <div>
              <h1 style={{
                fontSize: "clamp(22px,3vw,36px)", fontWeight: 900, letterSpacing: "-1.5px",
                background: "linear-gradient(135deg,#F1F5F9 30%,#38BDF8 70%)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", marginBottom: 8,
              }}>
                {wo.task}
              </h1>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {[
                  { label: `Vehicle ${wo.vehicle_id}`,  color: "#38BDF8" },
                  { label: wo.vehicle_model,             color: "#94A3B8" },
                  { label: wo.priority,                  color: priorityCol },
                  { label: wo.duration,                  color: "#A78BFA" },
                ].map(p => (
                  <span key={p.label} style={{ fontSize: 12, padding: "4px 12px", borderRadius: 20, background: `${p.color}14`, border: `1px solid ${p.color}40`, color: p.color, fontWeight: 600 }}>
                    {p.label}
                  </span>
                ))}
              </div>
            </div>

            {/* AI Confidence ring */}
            <div style={{ textAlign: "center" }}>
              <div style={{
                width: 72, height: 72, borderRadius: "50%",
                background: `conic-gradient(#A78BFA ${wo.confidence_score}%, rgba(255,255,255,0.06) 0)`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <div style={{ width: 58, height: 58, borderRadius: "50%", background: "#05070A", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <span style={{ fontSize: 15, fontWeight: 800, color: "#A78BFA" }}>{wo.confidence_score}%</span>
                </div>
              </div>
              <div style={{ fontSize: 10, color: "#475569", marginTop: 4 }}>AI Confidence</div>
            </div>
          </div>
        </div>

        {/* ── Progress Timeline ──────────────────────────────────────────────── */}
        <div className="glass" style={{ padding: "16px 24px", marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "#F1F5F9" }}>🔄 Repair Progress</h3>
            <span style={{ fontSize: 12, color: "#38BDF8", fontWeight: 600 }}>{status}</span>
          </div>
          <ProgressTimeline currentStatus={status} onChange={setStatus} />
          <p style={{ fontSize: 11, color: "#334155", textAlign: "center", marginTop: 4 }}>Click a stage to update progress</p>
        </div>

        {/* ── Checklist progress bar ─────────────────────────────────────────── */}
        <div style={{ marginBottom: 24, padding: "14px 20px", borderRadius: 12, background: "rgba(52,211,153,0.06)", border: "1px solid rgba(52,211,153,0.2)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 13 }}>
            <span style={{ color: "#94A3B8" }}>Checklist Progress</span>
            <span style={{ color: "#34D399", fontWeight: 700 }}>{checkedCount} / {wo.checklist.length} ({checkPct}%)</span>
          </div>
          <div style={{ height: 6, background: "rgba(255,255,255,0.06)", borderRadius: 4 }}>
            <div style={{ width: `${checkPct}%`, height: "100%", background: "linear-gradient(90deg,#34D399,#38BDF8)", borderRadius: 4, transition: "width 0.4s" }} />
          </div>
        </div>

        {/* ── Tab nav ───────────────────────────────────────────────────────── */}
        <div style={{ display: "flex", gap: 4, marginBottom: 20, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: 4, width: "fit-content" }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: "8px 16px", borderRadius: 9, border: activeTab === tab.id ? "1px solid rgba(56,189,248,0.25)" : "1px solid transparent",
                background: activeTab === tab.id ? "rgba(56,189,248,0.12)" : "transparent",
                color: activeTab === tab.id ? "#38BDF8" : "#475569",
                fontSize: 13, fontWeight: activeTab === tab.id ? 700 : 400, cursor: "pointer", transition: "all 0.15s",
              }}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* ── Tab: Overview ─────────────────────────────────────────────────── */}
        {activeTab === "overview" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <SectionCard title="📊 Diagnostics">
              <KVRow label="Health Score"    value={`${wo.health_score}%`}   color={healthColor(wo.health_score)} />
              <KVRow label="Failure Risk"    value={`${wo.failure_risk}%`}   color={wo.failure_risk > 70 ? "#EF4444" : "#FBBF24"} />
              <KVRow label="Remaining Life"  value={`${wo.rul_days} days`}   color={wo.rul_days < 7 ? "#EF4444" : "#34D399"} />
              <KVRow label="Risk Level"      value={wo.estimated_risk}       color={wo.estimated_risk === "Critical" ? "#EF4444" : "#FBBF24"} />
              <KVRow label="Root Causes"     value={wo.root_causes.join(", ") || "None"} />
            </SectionCard>

            <SectionCard title="🔧 Repair Details">
              <KVRow label="Task"            value={wo.task} />
              <KVRow label="Duration"        value={wo.duration}             color="#A78BFA" />
              <KVRow label="Technician"      value={wo.technician}           color="#38BDF8" />
              <KVRow label="Skill Required"  value={wo.technician_skill} />
              <KVRow label="Scheduled"       value={wo.scheduled_date} />
            </SectionCard>

            <SectionCard title="💰 Financial Impact">
              <KVRow label="Repair Cost"     value={`₹${wo.estimated_cost.toLocaleString("en-IN")}`}   color="#FBBF24" />
              <KVRow label="Failure Cost"    value={`₹${wo.failure_cost.toLocaleString("en-IN")}`}     color="#EF4444" />
              <KVRow label="Potential Savings" value={`₹${wo.potential_savings.toLocaleString("en-IN")}`} color="#34D399" />
            </SectionCard>

            <SectionCard title="🧠 AI Analysis">
              <p style={{ fontSize: 13, color: "#94A3B8", lineHeight: 1.7, marginBottom: 12 }}>{wo.ai_summary}</p>
              {wo.reasoning.slice(0, 3).map((r, i) => (
                <div key={i} style={{ fontSize: 12, color: "#64748B", padding: "4px 0 4px 10px", borderLeft: "2px solid rgba(167,139,250,0.3)", marginBottom: 4 }}>
                  {r}
                </div>
              ))}
            </SectionCard>
          </div>
        )}

        {/* ── Tab: Checklist ────────────────────────────────────────────────── */}
        {activeTab === "checklist" && (
          <div className="glass" style={{ padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: "#38BDF8" }}>✅ Repair Checklist</h3>
              <button
                onClick={() => setChecked(new Array(wo.checklist.length).fill(false))}
                style={{ fontSize: 11, padding: "4px 12px", borderRadius: 8, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#475569", cursor: "pointer" }}
              >
                Reset
              </button>
            </div>
            {wo.checklist.map((item, i) => (
              <CheckItem
                key={i}
                text={`${i + 1}. ${item}`}
                checked={checked[i]}
                onToggle={() => setChecked(prev => { const n = [...prev]; n[i] = !n[i]; return n; })}
              />
            ))}
          </div>
        )}

        {/* ── Tab: Instructions ─────────────────────────────────────────────── */}
        {activeTab === "instructions" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {(["before", "during", "after"] as const).map(phase => {
              const labels = { before: "🔴 Before Repair", during: "🟡 During Repair", after: "🟢 After Repair" };
              const colors2 = { before: "#EF4444", during: "#FBBF24", after: "#34D399" };
              return (
                <div key={phase} className="glass" style={{ padding: 24 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: colors2[phase], marginBottom: 14 }}>{labels[phase]}</h3>
                  {wo.instructions[phase].map((step, i) => (
                    <div key={i} style={{ display: "flex", gap: 12, padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <span style={{ fontSize: 12, color: colors2[phase], fontWeight: 700, minWidth: 20 }}>{i + 1}.</span>
                      <span style={{ fontSize: 13, color: "#CBD5E1", lineHeight: 1.5 }}>{step}</span>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        )}

        {/* ── Tab: Parts & Tools ────────────────────────────────────────────── */}
        {activeTab === "parts" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <SectionCard title="📦 Required Parts">
              {wo.parts.map((p, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#38BDF8", flexShrink: 0 }} />
                  <span style={{ fontSize: 13, color: "#CBD5E1" }}>{p}</span>
                </div>
              ))}
            </SectionCard>
            <SectionCard title="🔧 Required Tools">
              {wo.tools.map((t, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#A78BFA", flexShrink: 0 }} />
                  <span style={{ fontSize: 13, color: "#CBD5E1" }}>{t}</span>
                </div>
              ))}
            </SectionCard>
          </div>
        )}

      </div>
    </div>
  );
}

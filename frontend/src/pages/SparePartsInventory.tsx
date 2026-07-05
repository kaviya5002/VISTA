import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import Navbar from "../components/Navbar";

// ── Types ─────────────────────────────────────────────────────────────────────
interface Supplier {
  name: string; contact: string; lead_time: string;
  avg_delivery: number; reliability: number; last_purchase: string;
}
interface Part {
  id: string; name: string; category: string; category_color: string;
  current_stock: number; predicted_30d: number; remaining_after: number;
  min_stock: number; status: string; days_until_stockout: number | null;
  recommended_order: number; order_cost: number; unit_cost: number;
  lead_time_days: number; weekly_forecast: number[]; ai_insight: string;
  supplier: Supplier;
}
interface Category {
  category: string; color: string; total_parts: number;
  critical: number; total_predicted: number; total_order_cost: number;
}
interface Recommendation {
  part: string; order_qty: number; order_cost: number; status: string;
  days_left: number | null; supplier: string; lead_time: number; insight: string;
}
interface ForecastData {
  forecast_date: string; forecast_horizon: string;
  parts: Part[]; categories: Category[];
  summary: {
    total_parts: number; healthy_parts: number; critical_parts: number;
    stockout_parts: number; inventory_health: number;
    total_investment: number; vehicles_analyzed: number;
  };
  ai_recommendations: Recommendation[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const STATUS_COLOR: Record<string, string> = {
  "Healthy":      "#34D399",
  "Low Stock":    "#FBBF24",
  "Critical":     "#F97316",
  "Out of Stock": "#EF4444",
};
const STATUS_BG: Record<string, string> = {
  "Healthy":      "rgba(52,211,153,0.08)",
  "Low Stock":    "rgba(251,191,36,0.08)",
  "Critical":     "rgba(249,115,22,0.08)",
  "Out of Stock": "rgba(239,68,68,0.08)",
};
const STATUS_BORDER: Record<string, string> = {
  "Healthy":      "rgba(52,211,153,0.25)",
  "Low Stock":    "rgba(251,191,36,0.25)",
  "Critical":     "rgba(249,115,22,0.35)",
  "Out of Stock": "rgba(239,68,68,0.4)",
};
const STATUS_ICON: Record<string, string> = {
  "Healthy": "🟢", "Low Stock": "🟡", "Critical": "🟠", "Out of Stock": "🔴",
};

function sc(s: string) { return STATUS_COLOR[s] ?? "#94A3B8"; }

// ── Weekly Bar Chart ──────────────────────────────────────────────────────────
function WeeklyChart({ weeks, color }: { weeks: number[]; color: string }) {
  const max = Math.max(...weeks, 1);
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "flex-end", height: 40 }}>
      {weeks.map((v, i) => (
        <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
          <div style={{
            width: "100%", borderRadius: "3px 3px 0 0",
            height: `${Math.max(4, (v / max) * 36)}px`,
            background: v > 0 ? color : "rgba(255,255,255,0.06)",
            transition: "height 0.6s ease",
          }} />
          <span style={{ fontSize: 9, color: "#334155" }}>W{i + 1}</span>
        </div>
      ))}
    </div>
  );
}

// ── Stock Gauge ───────────────────────────────────────────────────────────────
function StockGauge({ current, predicted, min }: { current: number; predicted: number; min: number }) {
  const pct = Math.min(100, Math.round((current / Math.max(current + predicted, 1)) * 100));
  const color = pct > 60 ? "#34D399" : pct > 30 ? "#FBBF24" : "#EF4444";
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#475569", marginBottom: 3 }}>
        <span>Stock coverage</span><span style={{ color }}>{pct}%</span>
      </div>
      <div style={{ height: 5, background: "rgba(255,255,255,0.06)", borderRadius: 3 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3, transition: "width 0.8s" }} />
      </div>
    </div>
  );
}

// ── Part Card ─────────────────────────────────────────────────────────────────
function PartCard({ part, onSelect }: { part: Part; onSelect: (p: Part) => void }) {
  const col = sc(part.status);
  return (
    <div
      onClick={() => onSelect(part)}
      style={{
        padding: "16px 18px", borderRadius: 12, cursor: "pointer",
        background: STATUS_BG[part.status],
        border: `1px solid ${STATUS_BORDER[part.status]}`,
        transition: "all 0.2s",
      }}
      onMouseEnter={e => (e.currentTarget.style.transform = "translateY(-2px)")}
      onMouseLeave={e => (e.currentTarget.style.transform = "translateY(0)")}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, color: part.category_color, fontWeight: 700, marginBottom: 3 }}>
            {part.category}
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#F1F5F9", lineHeight: 1.3 }}>{part.name}</div>
        </div>
        <span style={{
          fontSize: 10, padding: "3px 8px", borderRadius: 10, flexShrink: 0, marginLeft: 8,
          background: `${col}18`, border: `1px solid ${col}44`, color: col, fontWeight: 700,
        }}>
          {STATUS_ICON[part.status]} {part.status}
        </span>
      </div>

      {/* Stock numbers */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6, marginBottom: 10 }}>
        {[
          { label: "Current",   val: part.current_stock,   color: "#F1F5F9" },
          { label: "Needed",    val: part.predicted_30d,   color: col },
          { label: "Remaining", val: part.remaining_after, color: part.remaining_after < 0 ? "#EF4444" : "#34D399" },
        ].map(r => (
          <div key={r.label} style={{ textAlign: "center", padding: "6px 4px", borderRadius: 6, background: "rgba(255,255,255,0.03)" }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: r.color }}>{r.val}</div>
            <div style={{ fontSize: 9, color: "#475569" }}>{r.label}</div>
          </div>
        ))}
      </div>

      {/* Stock gauge */}
      <StockGauge current={part.current_stock} predicted={part.predicted_30d} min={part.min_stock} />

      {/* Weekly chart */}
      <div style={{ marginTop: 10 }}>
        <div style={{ fontSize: 9, color: "#334155", marginBottom: 4 }}>30-day demand forecast</div>
        <WeeklyChart weeks={part.weekly_forecast} color={part.category_color} />
      </div>

      {/* Order badge */}
      {part.recommended_order > 0 && (
        <div style={{
          marginTop: 10, padding: "6px 10px", borderRadius: 8,
          background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.2)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{ fontSize: 11, color: "#38BDF8" }}>📦 Order {part.recommended_order} units</span>
          <span style={{ fontSize: 11, color: "#64748B" }}>₹{part.order_cost.toLocaleString("en-IN")}</span>
        </div>
      )}
    </div>
  );
}

// ── Part Detail Modal ─────────────────────────────────────────────────────────
function PartModal({ part, onClose }: { part: Part; onClose: () => void }) {
  const col = sc(part.status);
  return (
    <div
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, backdropFilter: "blur(4px)" }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{ background: "#0F172A", border: `1px solid ${STATUS_BORDER[part.status]}`, borderRadius: 16, padding: 28, width: 480, maxWidth: "92vw", maxHeight: "88vh", overflowY: "auto", boxShadow: `0 0 40px ${col}22` }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 11, color: part.category_color, fontWeight: 700, marginBottom: 4 }}>{part.category} · {part.id}</div>
            <h2 style={{ fontSize: 18, fontWeight: 800 }}>{part.name}</h2>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#475569", fontSize: 20, cursor: "pointer" }}>✕</button>
        </div>

        {/* Stock grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8, marginBottom: 18 }}>
          {[
            { label: "Current Stock",  val: part.current_stock,   color: "#F1F5F9" },
            { label: "30-Day Demand",  val: part.predicted_30d,   color: col },
            { label: "After Forecast", val: part.remaining_after, color: part.remaining_after < 0 ? "#EF4444" : "#34D399" },
            { label: "Safety Stock",   val: part.min_stock,       color: "#64748B" },
            { label: "Unit Cost",      val: `₹${part.unit_cost.toLocaleString("en-IN")}`, color: "#FBBF24" },
            { label: "Lead Time",      val: `${part.lead_time_days}d`, color: "#A78BFA" },
          ].map(r => (
            <div key={r.label} style={{ padding: "10px 12px", borderRadius: 8, background: "rgba(255,255,255,0.03)", textAlign: "center" }}>
              <div style={{ fontSize: 15, fontWeight: 800, color: r.color }}>{r.val}</div>
              <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>{r.label}</div>
            </div>
          ))}
        </div>

        {/* Weekly forecast chart */}
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 12, color: "#475569", marginBottom: 8 }}>📊 Weekly Demand Forecast</div>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end", height: 60 }}>
            {part.weekly_forecast.map((v, i) => {
              const max = Math.max(...part.weekly_forecast, 1);
              return (
                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                  <span style={{ fontSize: 11, color: part.category_color, fontWeight: 700 }}>{v}</span>
                  <div style={{ width: "100%", borderRadius: "4px 4px 0 0", height: `${Math.max(6, (v / max) * 44)}px`, background: v > 0 ? part.category_color : "rgba(255,255,255,0.06)", transition: "height 0.6s" }} />
                  <span style={{ fontSize: 10, color: "#334155" }}>Week {i + 1}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI Insight */}
        <div style={{ padding: "12px 14px", borderRadius: 10, background: "rgba(56,189,248,0.06)", border: "1px solid rgba(56,189,248,0.15)", marginBottom: 18 }}>
          <div style={{ fontSize: 11, color: "#38BDF8", fontWeight: 700, marginBottom: 6 }}>🧠 AI Insight</div>
          <p style={{ fontSize: 12, color: "#94A3B8", lineHeight: 1.6 }}>{part.ai_insight}</p>
        </div>

        {/* Supplier profile */}
        <div style={{ padding: "14px 16px", borderRadius: 10, background: "rgba(167,139,250,0.06)", border: "1px solid rgba(167,139,250,0.15)" }}>
          <div style={{ fontSize: 11, color: "#A78BFA", fontWeight: 700, marginBottom: 10 }}>🏭 Supplier Profile</div>
          {[
            { label: "Supplier",       val: part.supplier.name },
            { label: "Contact",        val: part.supplier.contact },
            { label: "Lead Time",      val: part.supplier.lead_time },
            { label: "Avg Delivery",   val: `${part.supplier.avg_delivery} days` },
            { label: "Reliability",    val: `${part.supplier.reliability}%` },
            { label: "Last Purchase",  val: part.supplier.last_purchase },
          ].map(r => (
            <div key={r.label} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid rgba(255,255,255,0.04)", fontSize: 12 }}>
              <span style={{ color: "#475569" }}>{r.label}</span>
              <span style={{ color: "#CBD5E1", fontWeight: 600 }}>{r.val}</span>
            </div>
          ))}
        </div>

        {part.recommended_order > 0 && (
          <div style={{ marginTop: 16, padding: "12px 16px", borderRadius: 10, background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.25)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#34D399" }}>📦 Recommended Order</div>
              <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>via {part.supplier.name}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: "#34D399" }}>{part.recommended_order} units</div>
              <div style={{ fontSize: 11, color: "#64748B" }}>₹{part.order_cost.toLocaleString("en-IN")}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function SparePartsInventory() {
  const [data,     setData]     = useState<ForecastData | null>(null);
  const [loading,  setLoading]  = useState(true);
  const [selected, setSelected] = useState<Part | null>(null);
  const [filterCat,    setFilterCat]    = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");
  const [searchQ,      setSearchQ]      = useState("");

  useEffect(() => {
    api.get("/spare-parts/forecast").then(r => {
      setData(r.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const parts = data?.parts ?? [];
  const summary = data?.summary;

  const filtered = useMemo(() =>
    parts.filter(p =>
      (filterCat    === "All" || p.category === filterCat) &&
      (filterStatus === "All" || p.status   === filterStatus) &&
      (searchQ === "" || p.name.toLowerCase().includes(searchQ.toLowerCase()))
    ), [parts, filterCat, filterStatus, searchQ]);

  const categories = [...new Set(parts.map(p => p.category))];

  return (
    <div style={{ background: "#05070A", minHeight: "100vh", paddingTop: 56 }}>
      <Navbar connected={false} />

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 32px 80px" }}>

        {/* ── Hero ──────────────────────────────────────────────────────────── */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <Link to="/" style={{ color: "#475569", fontSize: 13, textDecoration: "none" }}>← Dashboard</Link>
            <span style={{ color: "#1E293B" }}>/</span>
            <span style={{ color: "#38BDF8", fontSize: 13 }}>Spare Parts Forecast</span>
          </div>
          <h1 style={{
            fontSize: "clamp(22px,3vw,40px)", fontWeight: 900, letterSpacing: "-1.5px",
            background: "linear-gradient(135deg,#F1F5F9 30%,#FBBF24 70%)",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          }}>
            📦 AI Spare Parts Forecasting
          </h1>
          <p style={{ color: "#475569", fontSize: 14, marginTop: 6 }}>
            30-day demand forecast from Health · Failure · Root Cause · RUL models
            {data && <span style={{ color: "#334155" }}> · {summary?.vehicles_analyzed} vehicles analysed · {data.forecast_date}</span>}
          </p>
        </div>

        {/* ── Summary KPIs ──────────────────────────────────────────────────── */}
        {summary && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12, marginBottom: 28 }}>
            {[
              { label: "Inventory Health",  val: `${summary.inventory_health}%`, color: summary.inventory_health > 70 ? "#34D399" : "#FBBF24", sub: `${summary.healthy_parts}/${summary.total_parts} parts` },
              { label: "Critical Parts",    val: summary.critical_parts,         color: "#F97316",  sub: "need attention" },
              { label: "Out of Stock",      val: summary.stockout_parts,         color: "#EF4444",  sub: "immediate order" },
              { label: "Total Parts",       val: summary.total_parts,            color: "#38BDF8",  sub: "tracked" },
              { label: "Investment Needed", val: `₹${(summary.total_investment / 1000).toFixed(0)}K`, color: "#FBBF24", sub: "recommended orders" },
              { label: "Vehicles Analysed", val: summary.vehicles_analyzed,      color: "#A78BFA",  sub: "fleet-wide" },
            ].map(s => (
              <div key={s.label} className="glass" style={{ padding: "16px 18px" }}>
                <div style={{ fontSize: 22, fontWeight: 900, color: s.color }}>{s.val}</div>
                <div style={{ fontSize: 12, color: "#F1F5F9", fontWeight: 600, marginTop: 2 }}>{s.label}</div>
                <div style={{ fontSize: 11, color: "#334155", marginTop: 1 }}>{s.sub}</div>
              </div>
            ))}
          </div>
        )}

        {/* ── AI Recommendations ────────────────────────────────────────────── */}
        {data?.ai_recommendations && data.ai_recommendations.length > 0 && (
          <div style={{ marginBottom: 28 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "#FBBF24", marginBottom: 14 }}>
              🧠 AI Purchase Recommendations
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))", gap: 14 }}>
              {data.ai_recommendations.map((r, i) => (
                <div key={i} style={{
                  padding: "18px 20px", borderRadius: 12,
                  background: r.status === "Out of Stock" ? "rgba(239,68,68,0.07)" : r.status === "Critical" ? "rgba(249,115,22,0.07)" : "rgba(251,191,36,0.07)",
                  border: `1px solid ${sc(r.status)}33`,
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: "#F1F5F9" }}>{r.part}</div>
                      <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>via {r.supplier} · {r.lead_time}d lead</div>
                    </div>
                    <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 10, background: `${sc(r.status)}18`, color: sc(r.status), fontWeight: 700 }}>
                      {STATUS_ICON[r.status]} {r.status}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: "#94A3B8", lineHeight: 1.6, marginBottom: 12 }}>{r.insight}</p>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ fontSize: 12, color: "#34D399", fontWeight: 700 }}>📦 Order {r.order_qty} units</span>
                    <span style={{ fontSize: 12, color: "#FBBF24", fontWeight: 700 }}>₹{r.order_cost.toLocaleString("en-IN")}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Category breakdown ────────────────────────────────────────────── */}
        {data?.categories && (
          <div style={{ marginBottom: 28 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: "#38BDF8", marginBottom: 14 }}>📊 Category Overview</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 10 }}>
              {data.categories.map(cat => (
                <div
                  key={cat.category}
                  onClick={() => setFilterCat(filterCat === cat.category ? "All" : cat.category)}
                  style={{
                    padding: "14px 16px", borderRadius: 10, cursor: "pointer",
                    background: filterCat === cat.category ? `${cat.color}14` : "rgba(255,255,255,0.02)",
                    border: `1px solid ${filterCat === cat.category ? cat.color + "55" : "rgba(255,255,255,0.07)"}`,
                    transition: "all 0.15s",
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 700, color: cat.color, marginBottom: 6 }}>{cat.category}</div>
                  <div style={{ fontSize: 11, color: "#475569" }}>{cat.total_parts} parts</div>
                  {cat.critical > 0 && <div style={{ fontSize: 11, color: "#F97316", marginTop: 2 }}>⚠ {cat.critical} critical</div>}
                  <div style={{ fontSize: 11, color: "#334155", marginTop: 2 }}>~{cat.total_predicted} units needed</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Filters ───────────────────────────────────────────────────────── */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
          {/* Search */}
          <input
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
            placeholder="Search parts…"
            style={{
              padding: "7px 14px", borderRadius: 8, fontSize: 13,
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
              color: "#F1F5F9", outline: "none", width: 180,
            }}
          />
          {/* Status filter */}
          <div style={{ display: "flex", gap: 6 }}>
            {["All", "Healthy", "Low Stock", "Critical", "Out of Stock"].map(s => (
              <button
                key={s}
                onClick={() => setFilterStatus(s)}
                style={{
                  padding: "5px 12px", borderRadius: 20, fontSize: 11, fontWeight: 600, cursor: "pointer",
                  border: `1px solid ${filterStatus === s ? sc(s) : "rgba(255,255,255,0.1)"}`,
                  background: filterStatus === s ? `${sc(s)}18` : "transparent",
                  color: filterStatus === s ? sc(s) : "#475569", transition: "all 0.15s",
                }}
              >
                {s === "All" ? "All" : `${STATUS_ICON[s]} ${s}`}
              </button>
            ))}
          </div>
          {(filterCat !== "All" || filterStatus !== "All" || searchQ) && (
            <button
              onClick={() => { setFilterCat("All"); setFilterStatus("All"); setSearchQ(""); }}
              style={{ fontSize: 11, padding: "5px 12px", borderRadius: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#475569", cursor: "pointer" }}
            >
              ✕ Clear
            </button>
          )}
          <span style={{ fontSize: 12, color: "#334155", marginLeft: "auto" }}>
            {filtered.length} of {parts.length} parts
          </span>
        </div>

        {/* ── Parts Grid ────────────────────────────────────────────────────── */}
        {loading ? (
          <div style={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center", color: "#334155" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ width: 32, height: 32, border: "3px solid rgba(251,191,36,0.3)", borderTop: "3px solid #FBBF24", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 10px" }} />
              Forecasting spare parts demand…
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))", gap: 16 }}>
            {filtered.map(p => (
              <PartCard key={p.id} part={p} onSelect={setSelected} />
            ))}
            {filtered.length === 0 && (
              <div style={{ gridColumn: "1/-1", textAlign: "center", color: "#334155", padding: "40px 0", fontSize: 13 }}>
                No parts match the selected filters
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Detail Modal ──────────────────────────────────────────────────────── */}
      {selected && <PartModal part={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

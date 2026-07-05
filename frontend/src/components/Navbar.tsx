import { Link, useLocation } from "react-router-dom";

const NAV = [
  { path: "/",        label: "Command Center" },
  { path: "/alerts",  label: "Alerts" },
  { path: "/simulate",label: "Simulator" },
];

export default function Navbar({ connected }: { connected?: boolean }) {
  const { pathname } = useLocation();
  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "0 32px", height: 56,
      background: "rgba(5,7,10,0.85)",
      borderBottom: "1px solid rgba(255,255,255,0.07)",
      backdropFilter: "blur(24px)",
    }}>
      {/* Logo */}
      <Link to="/" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: "linear-gradient(135deg,#38BDF8,#6366F1)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14, fontWeight: 800, color: "#fff",
        }}>V</div>
        <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: "-0.3px" }}>VISTA</span>
        <span style={{ fontSize: 11, color: "#64748B", marginLeft: 2 }}>AI</span>
      </Link>

      {/* Links */}
      <div style={{ display: "flex", gap: 4 }}>
        {NAV.map(n => (
          <Link key={n.path} to={n.path} style={{
            padding: "5px 14px", borderRadius: 8, fontSize: 13,
            color: pathname === n.path ? "#38BDF8" : "#64748B",
            background: pathname === n.path ? "rgba(56,189,248,0.1)" : "transparent",
            border: pathname === n.path ? "1px solid rgba(56,189,248,0.2)" : "1px solid transparent",
            transition: "all 0.2s",
          }}>{n.label}</Link>
        ))}
      </div>

      {/* Live indicator */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
        <span style={{
          width: 7, height: 7, borderRadius: "50%",
          background: connected ? "#34D399" : "#F87171",
          boxShadow: connected ? "0 0 8px #34D399" : "0 0 8px #F87171",
          display: "inline-block",
          animation: connected ? "pulse 2s infinite" : "none",
        }} />
        <span style={{ color: connected ? "#34D399" : "#64748B" }}>
          {connected ? "Live" : "Offline"}
        </span>
      </div>

      <style>{`
        @keyframes pulse {
          0%,100% { opacity:1; }
          50% { opacity:0.4; }
        }
      `}</style>
    </nav>
  );
}

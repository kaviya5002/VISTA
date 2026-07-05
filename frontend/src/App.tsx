import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";

// Heavy pages — split into separate chunks, loaded only when navigated to
const VehicleDetails    = lazy(() => import("./pages/VehicleDetails"));
const Alerts            = lazy(() => import("./pages/Alerts"));
const ScenarioSimulator = lazy(() => import("./pages/ScenarioSimulator"));
const FleetReplay       = lazy(() => import("./pages/FleetReplay"));
const MaintenanceCalendar = lazy(() => import("./pages/MaintenanceCalendar"));
const WorkOrder         = lazy(() => import("./pages/WorkOrder"));
const TechnicianDashboard = lazy(() => import("./pages/TechnicianDashboard"));
const SparePartsInventory = lazy(() => import("./pages/SparePartsInventory"));
const DigitalTwin3D       = lazy(() => import("./pages/DigitalTwin"));

const PageFallback = () => (
  <div style={{
    minHeight: "100vh", background: "#05070A",
    display: "flex", alignItems: "center", justifyContent: "center",
    color: "#475569", fontSize: 14, gap: 12,
  }}>
    <div style={{
      width: 28, height: 28, border: "3px solid rgba(56,189,248,0.3)",
      borderTop: "3px solid #38BDF8", borderRadius: "50%",
      animation: "spin 0.8s linear infinite",
    }} />
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/vehicle/:id" element={<VehicleDetails />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/simulate" element={<ScenarioSimulator />} />
          <Route path="/replay" element={<FleetReplay />} />
          <Route path="/calendar" element={<MaintenanceCalendar />} />
          <Route path="/workorder/:id" element={<WorkOrder />} />
          <Route path="/technicians" element={<TechnicianDashboard />} />
          <Route path="/spare-parts" element={<SparePartsInventory />} />
          <Route path="/digital-twin" element={<DigitalTwin3D />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;

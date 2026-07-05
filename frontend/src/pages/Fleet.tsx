import { useAutoRefresh } from "../hooks/useAutoRefresh";
import FleetCharts from "../components/FleetCharts";
import { CACHE_TTL } from "../store/fleetStore";

function Fleet() {
  const { data: vehicles = [] } = useAutoRefresh<any[]>("fleet", "/fleet", CACHE_TTL.fleet);

  const totalVehicles = vehicles.length;
  const healthyVehicles = vehicles.filter((v: any) => v.status === "Healthy").length;
  const warningVehicles = vehicles.filter((v: any) => v.status === "Warning").length;
  const criticalVehicles = vehicles.filter((v: any) => v.status === "Critical").length;
  const totalSavings = vehicles.reduce((sum: number, v: any) => sum + v.potential_savings, 0);

  return (
    <div style={{ padding: "20px" }}>
      <h1>TwinGuard AI Dashboard</h1>

      <div style={{ display: "flex", gap: "20px", marginBottom: "30px" }}>
        <div>
          <h2>{totalVehicles}</h2>
          <p>Total Vehicles</p>
        </div>
        <div>
          <h2>{healthyVehicles}</h2>
          <p>Healthy</p>
        </div>
        <div>
          <h2>{warningVehicles}</h2>
          <p>Warning</p>
        </div>
        <div>
          <h2>{criticalVehicles}</h2>
          <p>Critical</p>
        </div>
        <div>
          <h2>₹{totalSavings}</h2>
          <p>Potential Savings</p>
        </div>
      </div>

      <FleetCharts
        healthy={healthyVehicles}
        warning={warningVehicles}
        critical={criticalVehicles}
      />

      <h2>Top Fleet Vehicles</h2>

      {vehicles.slice(0, 10).map((vehicle: any) => (
        <div
          key={vehicle.vehicle_id}
          style={{
            border: "1px solid #333",
            borderRadius: "12px",
            padding: "15px",
            marginBottom: "15px",
            backgroundColor: "#1a1a1a"
          }}
        >
          <h3>Vehicle {vehicle.vehicle_id}</h3>
          <p style={{
            color:
              vehicle.status === "Healthy" ? "lime"
              : vehicle.status === "Warning" ? "orange"
              : "red"
          }}>
            Status: {vehicle.status}
          </p>
          <p>Health: {vehicle.health_score}%</p>
          <p>Risk: {vehicle.failure_probability}%</p>
          <p>RUL: {vehicle.remaining_useful_life_days} Days</p>
          <p>Action: {vehicle.fleet_action}</p>
        </div>
      ))}
    </div>
  );
}

export default Fleet;

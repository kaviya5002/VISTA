import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

interface Props {
  currentHealth: number;
}

function getFutureStatus(health: number) {
  if (health > 70) return { label: "Stable", color: "lime" };
  if (health > 50) return { label: "Degrading", color: "yellow" };
  if (health > 30) return { label: "Critical", color: "orange" };
  if (health > 15) return { label: "Failure Imminent", color: "#ff6600" };
  return { label: "Breakdown Risk", color: "red" };
}

function DynamicTwin({ currentHealth }: Props) {
  // Project degradation over 30 days based on current health
  const degradationRate = currentHealth < 40 ? 5 : currentHealth < 70 ? 3 : 1.5;

  const predictions = [
    { day: 0,  battery: currentHealth },
    { day: 7,  battery: Math.max(0, Math.round(currentHealth - degradationRate * 1)) },
    { day: 15, battery: Math.max(0, Math.round(currentHealth - degradationRate * 2.5)) },
    { day: 30, battery: Math.max(0, Math.round(currentHealth - degradationRate * 5)) },
  ];

  return (
    <div>
      <h2>📈 Dynamic Digital Twin — 30 Day Forecast</h2>

      {/* Line Chart */}
      <div style={{ width: "100%", height: "250px", marginBottom: "20px" }}>
        <ResponsiveContainer>
          <LineChart data={predictions}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis
              dataKey="day"
              stroke="#aaa"
              tickFormatter={(v) => `Day ${v}`}
            />
            <YAxis stroke="#aaa" domain={[0, 100]} unit="%" />
            <Tooltip
              formatter={(value: any) => [`${value}%`, "Battery Health"]}
              labelFormatter={(label) => `Day ${label}`}
            />
            <Line
              type="monotone"
              dataKey="battery"
              stroke="#FF9800"
              strokeWidth={2}
              dot={{ fill: "#FF9800", r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Future Status Cards */}
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
        {predictions.map(({ day, battery }) => {
          const status = getFutureStatus(battery);
          return (
            <div
              key={day}
              style={{
                border: `1px solid ${status.color}`,
                borderRadius: "10px",
                padding: "12px 16px",
                backgroundColor: "#1a1a1a",
                minWidth: "120px",
                textAlign: "center"
              }}
            >
              <p style={{ color: "#aaa", marginBottom: "4px" }}>Day {day}</p>
              <p style={{ fontSize: "22px", fontWeight: "bold" }}>{battery}%</p>
              <p style={{ color: status.color, fontSize: "12px" }}>{status.label}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default DynamicTwin;

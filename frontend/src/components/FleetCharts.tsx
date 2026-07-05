import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

interface Props {
  healthy: number;
  warning: number;
  critical: number;
}

function FleetCharts({ healthy, warning, critical }: Props) {
  const data = [
    { name: "Healthy", value: healthy },
    { name: "Warning", value: warning },
    { name: "Critical", value: critical },
  ];

  const COLORS = ["#00C853", "#FF9800", "#F44336"];

  return (
    <div style={{ width: "400px", height: "300px" }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} dataKey="value" outerRadius={100} label>
            {data.map((_, index) => (
              <Cell key={index} fill={COLORS[index]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default FleetCharts;

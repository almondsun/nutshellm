import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function TokenChart({
  original,
  optimized,
}: {
  original: number;
  optimized: number;
}) {
  const data = [{ name: "Input", Original: original, Optimized: optimized }];
  return (
    <ResponsiveContainer width="100%" height={230}>
      <BarChart data={data} layout="vertical" margin={{ left: 0, right: 24 }}>
        <CartesianGrid stroke="#4b3324" horizontal={false} />
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="name" hide />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,.03)" }}
          contentStyle={{
            background: "#21160f",
            border: "1px solid #4b3324",
            borderRadius: "7px",
            color: "#f4e4c8",
          }}
        />
        <Bar dataKey="Original" fill="#77604e" radius={[0, 4, 4, 0]} />
        <Bar dataKey="Optimized" fill="#a8b85f" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

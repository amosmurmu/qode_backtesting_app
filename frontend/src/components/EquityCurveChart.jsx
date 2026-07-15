import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { Card, SectionLabel } from "./ui";
import { formatDate, formatINR } from "../utils/format";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-raised border border-border rounded-md px-3 py-2 text-xs font-mono shadow-lg">
      <div className="text-text-secondary mb-1">{formatDate(label)}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {formatINR(p.value)}
        </div>
      ))}
    </div>
  );
}

export default function EquityCurveChart({ equityCurve }) {
  const hasBenchmark = equityCurve.some((p) => p.benchmark_value != null);

  return (
    <Card className="p-5">
      <SectionLabel>Equity Curve{hasBenchmark ? " vs NIFTY 50" : ""}</SectionLabel>
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={equityCurve} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#5B8DEF" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#5B8DEF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1F2530" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            stroke="#565D6D"
            tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
            tickLine={false}
            axisLine={{ stroke: "#1F2530" }}
          />
          <YAxis
            tickFormatter={(v) => `₹${(v / 100000).toFixed(1)}L`}
            stroke="#565D6D"
            tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
            tickLine={false}
            axisLine={false}
            width={60}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12, fontFamily: "Inter" }} />
          <Area
            type="monotone"
            dataKey="portfolio_value"
            name="Strategy"
            stroke="#5B8DEF"
            strokeWidth={2}
            fill="url(#portfolioGradient)"
            dot={false}
          />
          {hasBenchmark && (
            <Area
              type="monotone"
              dataKey="benchmark_value"
              name="NIFTY 50"
              stroke="#8A92A3"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              fill="none"
              dot={false}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}

import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import { Card, SectionLabel } from "./ui";
import { formatDate, formatPct } from "../utils/format";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-raised border border-border rounded-md px-3 py-2 text-xs font-mono shadow-lg">
      <div className="text-text-secondary mb-1">{formatDate(label)}</div>
      <div className="text-loss">{formatPct(payload[0].value)}</div>
    </div>
  );
}

export default function DrawdownChart({ drawdownCurve }) {
  return (
    <Card className="p-5">
      <SectionLabel>Drawdown</SectionLabel>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={drawdownCurve} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#F87171" stopOpacity={0} />
              <stop offset="100%" stopColor="#F87171" stopOpacity={0.35} />
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
            tickFormatter={(v) => `${v.toFixed(0)}%`}
            stroke="#565D6D"
            tick={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
            tickLine={false}
            axisLine={false}
            width={45}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="portfolio_value"
            stroke="#F87171"
            strokeWidth={1.5}
            fill="url(#drawdownGradient)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}

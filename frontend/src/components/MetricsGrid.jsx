import { Card } from "./ui";
import { formatPct, formatNumber, signColor } from "../utils/format";

function MetricTile({ label, value, colorClass = "text-text-primary", sublabel }) {
  return (
    <div className="bg-surface-raised border border-border rounded-md px-4 py-3">
      <div className="text-xs text-text-secondary mb-1">{label}</div>
      <div className={`font-mono text-xl font-semibold ${colorClass}`}>{value}</div>
      {sublabel && <div className="text-xs text-text-faint mt-0.5">{sublabel}</div>}
    </div>
  );
}

export default function MetricsGrid({ metrics }) {
  if (!metrics) return null;

  return (
    <Card className="p-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricTile
          label="CAGR"
          value={formatPct(metrics.cagr_pct, { showSign: true })}
          colorClass={signColor(metrics.cagr_pct)}
          sublabel={metrics.benchmark_cagr_pct != null ? `NIFTY: ${formatPct(metrics.benchmark_cagr_pct)}` : undefined}
        />
        <MetricTile
          label="Total Return"
          value={formatPct(metrics.total_return_pct, { showSign: true })}
          colorClass={signColor(metrics.total_return_pct)}
        />
        <MetricTile label="Sharpe Ratio" value={formatNumber(metrics.sharpe_ratio)} />
        <MetricTile
          label="Max Drawdown"
          value={formatPct(metrics.max_drawdown_pct)}
          colorClass="text-loss"
          sublabel={metrics.benchmark_max_drawdown_pct != null ? `NIFTY: ${formatPct(metrics.benchmark_max_drawdown_pct)}` : undefined}
        />
        <MetricTile label="Volatility (Ann.)" value={formatPct(metrics.annualized_volatility_pct)} />
        <MetricTile label="Win Rate" value={formatPct(metrics.win_rate_pct)} />
        <MetricTile
          label="Best Period"
          value={formatPct(metrics.best_period_return_pct, { showSign: true })}
          colorClass="text-gain"
        />
        <MetricTile
          label="Worst Period"
          value={formatPct(metrics.worst_period_return_pct, { showSign: true })}
          colorClass="text-loss"
        />
      </div>
    </Card>
  );
}

import { Card, SectionLabel } from "./ui";
import { formatPct } from "../utils/format";

function StockList({ title, stocks, accentClass }) {
  return (
    <div>
      <div className="text-xs font-medium text-text-secondary mb-2">{title}</div>
      <div className="space-y-1">
        {stocks.length === 0 && <div className="text-xs text-text-faint">No data</div>}
        {stocks.map((s) => (
          <div key={s.ticker} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-surface-raised">
            <div>
              <span className="font-mono text-sm text-text-primary">{s.ticker.replace(".NS", "")}</span>
              <span className="text-xs text-text-faint ml-2">{s.name}</span>
            </div>
            <span className={`font-mono text-sm font-medium ${accentClass}`}>
              {formatPct(s.total_return_pct, { showSign: true })}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function WinnersLosersTable({ topWinners, topLosers }) {
  return (
    <Card className="p-5">
      <SectionLabel>Top Winners &amp; Losers</SectionLabel>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-2">
        <StockList title="Winners" stocks={topWinners} accentClass="text-gain" />
        <StockList title="Losers" stocks={topLosers} accentClass="text-loss" />
      </div>
    </Card>
  );
}

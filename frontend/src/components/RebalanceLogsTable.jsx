import { useState } from "react";
import { Card, SectionLabel, SecondaryButton } from "./ui";
import { formatDate, formatINR, formatNumber } from "../utils/format";
import { downloadCSV, flattenRebalanceLogs } from "../utils/csv";

export default function RebalanceLogsTable({ rebalanceLogs }) {
  const [expandedIdx, setExpandedIdx] = useState(0);

  const handleExportCSV = () => {
    const rows = flattenRebalanceLogs(rebalanceLogs);
    downloadCSV("portfolio_logs.csv", rows);
  };

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-3">
        <SectionLabel>Portfolio Logs</SectionLabel>
        <SecondaryButton onClick={handleExportCSV}>Export CSV</SecondaryButton>
      </div>

      <div className="space-y-2">
        {rebalanceLogs.map((log, idx) => {
          const isOpen = expandedIdx === idx;
          return (
            <div key={log.rebalance_date} className="border border-border rounded-md overflow-hidden">
              <button
                type="button"
                onClick={() => setExpandedIdx(isOpen ? -1 : idx)}
                className="w-full flex items-center justify-between px-4 py-3 bg-surface-raised hover:bg-border transition-colors"
              >
                <span className="font-mono text-sm text-text-primary">{formatDate(log.rebalance_date)}</span>
                <div className="flex items-center gap-4">
                  <span className="font-mono text-sm text-text-secondary">{formatINR(log.portfolio_value)}</span>
                  <span className="text-text-faint text-xs">{log.holdings.length} holdings</span>
                  <svg
                    width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                    className={`text-text-secondary transition-transform ${isOpen ? "rotate-180" : ""}`}
                  >
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </div>
              </button>

              {isOpen && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-text-faint text-xs border-b border-border">
                        <th className="text-left px-4 py-2 font-medium">Ticker</th>
                        <th className="text-left px-4 py-2 font-medium">Name</th>
                        <th className="text-right px-4 py-2 font-medium">Weight</th>
                        <th className="text-right px-4 py-2 font-medium">Shares</th>
                        <th className="text-right px-4 py-2 font-medium">Entry Price</th>
                      </tr>
                    </thead>
                    <tbody>
                      {log.holdings.map((h) => (
                        <tr key={h.ticker} className="border-b border-border-soft last:border-0">
                          <td className="px-4 py-2 font-mono text-text-primary">{h.ticker.replace(".NS", "")}</td>
                          <td className="px-4 py-2 text-text-secondary text-xs">{h.name}</td>
                          <td className="px-4 py-2 font-mono text-right text-text-primary">{(h.weight * 100).toFixed(2)}%</td>
                          <td className="px-4 py-2 font-mono text-right text-text-secondary">{formatNumber(h.shares, 2)}</td>
                          <td className="px-4 py-2 font-mono text-right text-text-secondary">{formatINR(h.entry_price)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

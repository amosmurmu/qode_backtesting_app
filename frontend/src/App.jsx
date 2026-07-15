import { useState, useEffect, useCallback } from "react";
import StrategyForm from "./components/StrategyForm";
import EquityCurveChart from "./components/EquityCurveChart";
import DrawdownChart from "./components/DrawdownChart";
import MetricsGrid from "./components/MetricsGrid";
import WinnersLosersTable from "./components/WinnersLosersTable";
import RebalanceLogsTable from "./components/RebalanceLogsTable";
import WarningsBanner from "./components/WarningsBanner";
import DataCoverageBadge from "./components/DataCoverageBadge";
import { runBacktest, getAvailableMetrics, getDataCoverage } from "./api/client";
import { FALLBACK_METRICS } from "./utils/constants";

export default function App() {
  const [metrics, setMetrics] = useState(FALLBACK_METRICS);
  const [coverage, setCoverage] = useState(null);
  const [result, setResult] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAvailableMetrics().then(setMetrics).catch(() => {});
    getDataCoverage().then(setCoverage).catch(() => setCoverage({ stocks: 0 }));
  }, []);

  const handleRun = useCallback(async (payload) => {
    setIsRunning(true);
    setError(null);
    try {
      const data = await runBacktest(payload);
      setResult(data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Backtest failed. Check the backend logs for details.");
      setResult(null);
    } finally {
      setIsRunning(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border px-6 py-4 flex items-center justify-between sticky top-0 bg-bg/95 backdrop-blur-sm z-10">
        <div>
          <h1 className="font-display text-lg font-semibold text-text-primary">Qode Backtester</h1>
          <p className="text-xs text-text-faint mt-0.5">Equity fundamental strategy backtesting</p>
        </div>
        <DataCoverageBadge coverage={coverage} />
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-8">
        <aside>
          <StrategyForm metrics={metrics} coverage={coverage} onSubmit={handleRun} isRunning={isRunning} />
        </aside>

        <section className="space-y-6">
          {error && (
            <div className="bg-loss-soft border border-loss/30 rounded-md px-4 py-3 text-sm text-loss">
              {error}
            </div>
          )}

          {!result && !error && (
            <div className="flex items-center justify-center h-64 border border-dashed border-border rounded-lg">
              <p className="text-text-faint text-sm">
                Configure a strategy on the left and run a backtest to see results here.
              </p>
            </div>
          )}

          {result && (
            <>
              <WarningsBanner warnings={result.warnings} />
              <MetricsGrid metrics={result.metrics} />
              <EquityCurveChart equityCurve={result.equity_curve} />
              <DrawdownChart drawdownCurve={result.drawdown_curve} />
              <WinnersLosersTable topWinners={result.top_winners} topLosers={result.top_losers} />
              <RebalanceLogsTable rebalanceLogs={result.rebalance_logs} />
            </>
          )}
        </section>
      </main>
    </div>
  );
}

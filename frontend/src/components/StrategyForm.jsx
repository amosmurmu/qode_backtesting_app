import { useState, useEffect } from "react";
import { Card, SectionLabel, PrimaryButton, SecondaryButton, IconButton } from "./ui";
import {
  REBALANCE_OPTIONS,
  WEIGHTING_OPTIONS,
  OPERATOR_OPTIONS,
  DIRECTION_OPTIONS,
} from "../utils/constants";

const inputClass =
  "w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-sm text-text-primary " +
  "font-mono placeholder:text-text-faint focus:border-accent focus:outline-none transition-colors";

const labelClass = "block text-xs font-medium text-text-secondary mb-1.5";

function FilterRow({ filter, metrics, onChange, onRemove }) {
  return (
    <div className="flex items-center gap-2">
      <select
        className={inputClass}
        value={filter.metric}
        onChange={(e) => onChange({ ...filter, metric: e.target.value })}
      >
        {metrics.map((m) => (
          <option key={m.key} value={m.key}>{m.label}</option>
        ))}
      </select>
      <select
        className={`${inputClass} max-w-[140px]`}
        value={filter.operator}
        onChange={(e) => onChange({ ...filter, operator: e.target.value })}
      >
        {OPERATOR_OPTIONS.map((op) => (
          <option key={op.value} value={op.value}>{op.label}</option>
        ))}
      </select>
      <input
        type="number"
        className={`${inputClass} max-w-[120px]`}
        value={filter.value}
        onChange={(e) => onChange({ ...filter, value: parseFloat(e.target.value) || 0 })}
      />
      <IconButton onClick={onRemove} title="Remove filter">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </IconButton>
    </div>
  );
}

function RankRow({ rule, metrics, onChange, onRemove }) {
  return (
    <div className="flex items-center gap-2">
      <select
        className={inputClass}
        value={rule.metric}
        onChange={(e) => onChange({ ...rule, metric: e.target.value })}
      >
        {metrics.map((m) => (
          <option key={m.key} value={m.key}>{m.label}</option>
        ))}
      </select>
      <select
        className={`${inputClass} max-w-[230px]`}
        value={rule.direction}
        onChange={(e) => onChange({ ...rule, direction: e.target.value })}
      >
        {DIRECTION_OPTIONS.map((d) => (
          <option key={d.value} value={d.value}>{d.label}</option>
        ))}
      </select>
      <input
        type="number"
        step="0.1"
        min="0"
        className={`${inputClass} max-w-[90px]`}
        value={rule.weight}
        onChange={(e) => onChange({ ...rule, weight: parseFloat(e.target.value) || 0 })}
        title="Relative weight in composite rank"
      />
      <IconButton onClick={onRemove} title="Remove rank rule">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </IconButton>
    </div>
  );
}

export default function StrategyForm({ metrics, coverage, onSubmit, isRunning }) {
  const [startDate, setStartDate] = useState("2022-01-01");
  const [endDate, setEndDate] = useState("2025-12-31");
  const [rebalanceFrequency, setRebalanceFrequency] = useState("quarterly");
  const [portfolioSize, setPortfolioSize] = useState(20);
  const [weightingMethod, setWeightingMethod] = useState("equal");
  const [weightingMetric, setWeightingMetric] = useState(metrics[0]?.key || "roce_pct");
  const [initialCapital, setInitialCapital] = useState(1000000);

  const [filters, setFilters] = useState([
    { metric: "market_cap_cr", operator: ">", value: 1000 },
    { metric: "pat_cr", operator: ">", value: 0 },
  ]);
  const [rankRules, setRankRules] = useState([
    { metric: "roe_pct", direction: "desc", weight: 1 },
  ]);

  const [priceStart, priceEnd] = coverage?.price_date_range || [];

  useEffect(() => {
    if (!priceStart || !priceEnd) return;
    setStartDate((prev) => (prev < priceStart ? priceStart : prev));
    setEndDate((prev) => (prev > priceEnd ? priceEnd : prev));
  }, [priceStart, priceEnd]);

  const addFilter = () =>
    setFilters([...filters, { metric: metrics[0]?.key || "roce_pct", operator: ">", value: 0 }]);
  const addRankRule = () =>
    setRankRules([...rankRules, { metric: metrics[0]?.key || "roe_pct", direction: "desc", weight: 1 }]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const capital = Number(initialCapital);
    if (!capital || capital <= 0) return;
    onSubmit({
      start_date: startDate,
      end_date: endDate,
      rebalance_frequency: rebalanceFrequency,
      portfolio_size: Number(portfolioSize),
      weighting_method: weightingMethod,
      weighting_metric: weightingMethod === "metric" ? weightingMetric : null,
      filters,
      rank_rules: rankRules,
      initial_capital: capital,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* --- Basics --- */}
      <Card className="p-5">
        <SectionLabel>Backtest Window</SectionLabel>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>Start date</label>
            <input
              type="date"
              className={inputClass}
              value={startDate}
              min={priceStart}
              max={priceEnd || undefined}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>
          <div>
            <label className={labelClass}>End date</label>
            <input
              type="date"
              className={inputClass}
              value={endDate}
              min={priceStart}
              max={priceEnd || undefined}
              onChange={(e) => setEndDate(e.target.value)}
              required
            />
          </div>
        </div>
        {priceStart && priceEnd && (
          <p className="text-xs text-text-faint mt-2">
            Price data available: {priceStart} → {priceEnd}
          </p>
        )}

        <div className="grid grid-cols-2 gap-4 mt-4">
          <div>
            <label className={labelClass}>Rebalance frequency</label>
            <select className={inputClass} value={rebalanceFrequency} onChange={(e) => setRebalanceFrequency(e.target.value)}>
              {REBALANCE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className={labelClass}>Portfolio size (top N)</label>
            <input type="number" min="1" max="50" className={inputClass} value={portfolioSize} onChange={(e) => setPortfolioSize(e.target.value)} required />
          </div>
        </div>

        <div className="mt-4">
          <label className={labelClass}>Initial capital (₹)</label>
          <input
            type="text"
            inputMode="numeric"
            className={inputClass}
            value={initialCapital}
            onChange={(e) => setInitialCapital(e.target.value.replace(/[^\d]/g, ""))}
            placeholder="1000000"
            required
          />
        </div>
      </Card>

      {/* --- Weighting --- */}
      <Card className="p-5">
        <SectionLabel>Position Sizing</SectionLabel>
        <select className={inputClass} value={weightingMethod} onChange={(e) => setWeightingMethod(e.target.value)}>
          {WEIGHTING_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {weightingMethod === "metric" && (
          <div className="mt-3">
            <label className={labelClass}>Weight by metric</label>
            <select className={inputClass} value={weightingMetric} onChange={(e) => setWeightingMetric(e.target.value)}>
              {metrics.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
            </select>
          </div>
        )}
      </Card>

      {/* --- Filters --- */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <SectionLabel>Filters <span className="text-text-faint normal-case font-normal">(applied once, used every rebalance)</span></SectionLabel>
        </div>
        <div className="space-y-2">
          {filters.map((f, i) => (
            <FilterRow
              key={i}
              filter={f}
              metrics={metrics}
              onChange={(updated) => setFilters(filters.map((x, idx) => (idx === i ? updated : x)))}
              onRemove={() => setFilters(filters.filter((_, idx) => idx !== i))}
            />
          ))}
        </div>
        <SecondaryButton onClick={addFilter} className="mt-3">+ Add filter</SecondaryButton>
      </Card>

      {/* --- Ranking --- */}
      <Card className="p-5">
        <SectionLabel>Ranking <span className="text-text-faint normal-case font-normal">(composite score across rules)</span></SectionLabel>
        <div className="space-y-2">
          {rankRules.map((r, i) => (
            <RankRow
              key={i}
              rule={r}
              metrics={metrics}
              onChange={(updated) => setRankRules(rankRules.map((x, idx) => (idx === i ? updated : x)))}
              onRemove={() => setRankRules(rankRules.filter((_, idx) => idx !== i))}
            />
          ))}
        </div>
        <SecondaryButton onClick={addRankRule} className="mt-3">+ Add rank rule</SecondaryButton>
      </Card>

      <PrimaryButton type="submit" disabled={isRunning} className="w-full py-3 text-base">
        {isRunning ? "Running backtest…" : "Run backtest"}
      </PrimaryButton>
    </form>
  );
}

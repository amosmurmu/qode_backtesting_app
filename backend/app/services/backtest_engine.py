"""
The backtest engine.

This module has ZERO knowledge of FastAPI, HTTP, or the database session
lifecycle - it's pure logic that takes pandas DataFrames in and returns
results out. That separation means you can unit-test it directly, or
reuse it from a CLI script, without spinning up a web server.

------------------------------------------------------------------------
THE NO-LOOKAHEAD-BIAS RULE (read this before touching ranking logic)
------------------------------------------------------------------------
On every rebalance date, we are only allowed to use fundamental data that
was ALREADY PUBLISHED by that date. A company's Q4 FY25 results announced
in May can't be used to pick stocks in March. We enforce this with one
rule, applied everywhere fundamentals are read:

    metrics_as_of(rebalance_date) = the latest FinancialMetric row per
    stock where as_of_date <= rebalance_date

This is the single most important correctness property of the whole
engine. If you ever change ranking/filtering code, check this rule still
holds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from app.schemas.backtest import (
    BacktestRequest,
    WeightingMethod,
    RebalanceFrequency,
)

TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE_ANNUAL = 0.065  # ~ Indian 10Y G-Sec ballpark, used for Sharpe


@dataclass
class RebalanceResult:
    rebalance_date: date
    weights: dict[str, float]  # ticker -> weight (sums to 1.0)
    entry_prices: dict[str, float]
    portfolio_value_before: float


@dataclass
class BacktestState:
    """Accumulates results as the engine walks forward through time."""

    equity_curve: list[tuple[date, float]] = field(default_factory=list)
    benchmark_curve: list[tuple[date, float]] = field(default_factory=list)
    rebalance_history: list[RebalanceResult] = field(default_factory=list)
    period_returns: list[float] = field(default_factory=list)  # one per rebalance period
    per_stock_total_return: dict[str, list[float]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def get_rebalance_dates(
    start: date, end: date, frequency: RebalanceFrequency
) -> list[date]:
    """
    Generate the list of rebalance dates between start and end.
    Uses pandas date_range so we don't hand-roll calendar math.
    """
    freq_map = {
        RebalanceFrequency.monthly: "MS",  # month start
        RebalanceFrequency.quarterly: "QS",
        RebalanceFrequency.yearly: "YS",
    }
    dates = pd.date_range(start=start, end=end, freq=freq_map[frequency.value])
    result = [d.date() for d in dates]
    if not result or result[0] != start:
        result.insert(0, start)
    return result


def apply_filters(
    metrics_df: pd.DataFrame, filters: list
) -> pd.DataFrame:
    """
    Apply the filtering system ONCE per rebalance, on that rebalance's
    as-of fundamentals snapshot. filters is a list of FilterRule
    (metric, operator, value).
    """
    ops = {
        ">": lambda s, v: s > v,
        ">=": lambda s, v: s >= v,
        "<": lambda s, v: s < v,
        "<=": lambda s, v: s <= v,
        "==": lambda s, v: s == v,
    }
    out = metrics_df.copy()
    for f in filters:
        if f.metric not in out.columns:
            continue  # unknown metric column - skip rather than crash the run
        if f.operator not in ops:
            raise ValueError(f"Unsupported filter operator: {f.operator}")
        mask = ops[f.operator](out[f.metric], f.value) & out[f.metric].notna()
        out = out[mask]
    return out


def apply_ranking(metrics_df: pd.DataFrame, rank_rules: list) -> pd.DataFrame:
    """
    Composite ranking: for each rank rule, compute a percentile rank
    (0 = worst, 1 = best after direction is applied), then take the
    weighted average across rules. Lower composite "rank_score" wins
    is inverted to "higher is better" for clarity - higher final score
    = more desirable stock.

    Using percentile rank (not raw rank position) means metrics with
    different scales (PE ~20, ROCE ~15%) combine fairly without one
    metric dominating just because it has more spread.
    """
    if not rank_rules:
        return metrics_df

    out = metrics_df.copy()
    total_weight = sum(r.weight for r in rank_rules) or 1.0
    composite = pd.Series(0.0, index=out.index)

    for rule in rank_rules:
        if rule.metric not in out.columns:
            continue
        col = out[rule.metric]
        pct_rank = col.rank(pct=True, na_option="bottom")
        if rule.direction.value == "asc":
            # ascending = smaller raw value is better (e.g. PE ascending)
            pct_rank = 1 - pct_rank
        composite += pct_rank.fillna(0) * (rule.weight / total_weight)

    out["composite_score"] = composite
    return out.sort_values("composite_score", ascending=False)


def compute_weights(
    selected: pd.DataFrame, method: WeightingMethod, weighting_metric: str | None
) -> dict[str, float]:
    """
    Turn a selected list of tickers into portfolio weights summing to 1.0.
    """
    if selected.empty:
        return {}

    if method == WeightingMethod.equal:
        w = 1.0 / len(selected)
        return {row.ticker: w for row in selected.itertuples()}

    if method == WeightingMethod.market_cap:
        caps = selected["market_cap_cr"].clip(lower=0).fillna(0)
        total = caps.sum()
        if total <= 0:
            # fall back to equal-weight if market cap data is missing
            w = 1.0 / len(selected)
            return {row.ticker: w for row in selected.itertuples()}
        return dict(zip(selected["ticker"], caps / total))

    if method == WeightingMethod.metric:
        col = selected[weighting_metric].clip(lower=0).fillna(0)
        total = col.sum()
        if total <= 0:
            w = 1.0 / len(selected)
            return {row.ticker: w for row in selected.itertuples()}
        return dict(zip(selected["ticker"], col / total))

    raise ValueError(f"Unknown weighting method: {method}")


def latest_metrics_as_of(
    all_metrics: pd.DataFrame, as_of: date
) -> pd.DataFrame:
    """
    THE no-lookahead-bias guard. For each stock, keep only the most recent
    FinancialMetric row whose as_of_date <= the rebalance date, then drop
    the as_of_date column (it's done its job).

    all_metrics columns expected: ticker, name, as_of_date, <metric cols...>
    """
    eligible = all_metrics[all_metrics["as_of_date"] <= as_of]
    if eligible.empty:
        return eligible
    # sort so the most recent as_of_date per ticker is last, then keep last
    eligible = eligible.sort_values("as_of_date")
    latest = eligible.groupby("ticker", as_index=False).tail(1)
    return latest.reset_index(drop=True)


def price_on_or_before(prices_df: pd.DataFrame, ticker: str, target: date) -> float | None:
    """
    Get a stock's price on `target` date, or the most recent trading day
    before it (handles weekends/holidays without crashing).
    prices_df columns: ticker, trade_date, adj_close
    """
    rows = prices_df[(prices_df["ticker"] == ticker) & (prices_df["trade_date"] <= target)]
    if rows.empty:
        return None
    return float(rows.sort_values("trade_date").iloc[-1]["adj_close"])


def benchmark_price_on_or_before(benchmark_df: pd.DataFrame, target: date) -> float | None:
    """
    Same idea as price_on_or_before, but for the single-series benchmark
    DataFrame (columns: trade_date, adj_close - no ticker column).
    """
    rows = benchmark_df[benchmark_df["trade_date"] <= target]
    if rows.empty:
        return None
    return float(rows.sort_values("trade_date").iloc[-1]["adj_close"])


def run_backtest(
    request: BacktestRequest,
    prices_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    name_lookup: dict[str, str],
    benchmark_df: pd.DataFrame | None = None,
) -> BacktestState:
    """
    The main walk-forward loop.

    prices_df:   columns [ticker, trade_date, adj_close]   (all stocks, all dates)
    metrics_df:  columns [ticker, as_of_date, <fundamental columns>]
    benchmark_df: columns [trade_date, adj_close]  (e.g. NIFTY 50), optional

    Algorithm per rebalance date:
      1. Take fundamentals as-of that date only (no future leakage).
      2. Apply filters once -> eligible universe for this period.
      3. Rank eligible universe -> take top `portfolio_size`.
      4. Compute weights (equal / market-cap / metric).
      5. Price the portfolio using THAT day's close -> buy.
      6. Hold until next rebalance date, then mark-to-market using each
         stock's price on the next rebalance date -> compute period return.
      7. Compound capital: new_capital = old_capital * (1 + period_return).
    """
    state = BacktestState()
    rebalance_dates = get_rebalance_dates(request.start_date, request.end_date, request.rebalance_frequency)

    capital = request.initial_capital
    state.equity_curve.append((rebalance_dates[0], capital))

    bench_start_price = None
    if benchmark_df is not None and not benchmark_df.empty:
        bench_start_price = benchmark_price_on_or_before(benchmark_df, rebalance_dates[0])
    state.benchmark_curve.append((rebalance_dates[0], request.initial_capital))

    def record_point(point_date: date, port_value: float) -> None:
        """Append one (date, value) pair to BOTH the equity curve and the
        parallel benchmark curve, so the two series always stay aligned
        index-for-index - this is what lets the frontend overlay them on
        one chart without a separate date-matching step."""
        state.equity_curve.append((point_date, port_value))
        if bench_start_price:
            bench_now = benchmark_price_on_or_before(benchmark_df, point_date)
            bench_val = (
                request.initial_capital * (bench_now / bench_start_price)
                if bench_now else state.benchmark_curve[-1][1]
            )
        else:
            bench_val = state.benchmark_curve[-1][1]
        state.benchmark_curve.append((point_date, bench_val))

    for i, reb_date in enumerate(rebalance_dates):
        as_of_metrics = latest_metrics_as_of(metrics_df, reb_date)

        if as_of_metrics.empty:
            state.warnings.append(
                f"No fundamental data available as of {reb_date}; skipping this rebalance."
            )
            record_point(reb_date, capital)
            continue

        eligible = apply_filters(as_of_metrics, request.filters)
        if eligible.empty:
            state.warnings.append(
                f"No stocks passed the filters on {reb_date}; holding cash this period."
            )
            record_point(reb_date, capital)
            continue

        ranked = apply_ranking(eligible, request.rank_rules)
        selected = ranked.head(request.portfolio_size)

        weights = compute_weights(selected, request.weighting_method, request.weighting_metric)

        entry_prices: dict[str, float] = {}
        for ticker in weights:
            p = price_on_or_before(prices_df, ticker, reb_date)
            if p:
                entry_prices[ticker] = p

        # Drop any ticker we couldn't price, and renormalize remaining weights
        weights = {t: w for t, w in weights.items() if t in entry_prices}
        if not weights:
            state.warnings.append(f"No priceable stocks on {reb_date}; holding cash this period.")
            record_point(reb_date, capital)
            continue
        total_w = sum(weights.values())
        weights = {t: w / total_w for t, w in weights.items()}

        state.rebalance_history.append(
            RebalanceResult(
                rebalance_date=reb_date,
                weights=weights,
                entry_prices=entry_prices,
                portfolio_value_before=capital,
            )
        )

        # Determine the holding period end (next rebalance date, or the
        # final end_date if this is the last period).
        period_end = rebalance_dates[i + 1] if i + 1 < len(rebalance_dates) else request.end_date

        # Mark-to-market each holding at period end, compute period return.
        period_return = 0.0
        for ticker, w in weights.items():
            exit_price = price_on_or_before(prices_df, ticker, period_end)
            entry_price = entry_prices[ticker]
            if exit_price is None or entry_price == 0:
                stock_return = 0.0
            else:
                stock_return = (exit_price - entry_price) / entry_price
            period_return += w * stock_return
            state.per_stock_total_return.setdefault(ticker, []).append(stock_return)

        state.period_returns.append(period_return)
        capital = capital * (1 + period_return)
        record_point(period_end, capital)

    return state


# ---------------------------------------------------------------------------
# Performance metrics
# ---------------------------------------------------------------------------

def compute_cagr(start_value: float, end_value: float, years: float) -> float:
    if start_value <= 0 or years <= 0:
        return 0.0
    return ((end_value / start_value) ** (1 / years) - 1) * 100


def compute_max_drawdown(equity_values: list[float]) -> float:
    """Largest peak-to-trough decline, expressed as a negative percentage."""
    if not equity_values:
        return 0.0
    arr = np.array(equity_values)
    running_max = np.maximum.accumulate(arr)
    drawdowns = (arr - running_max) / running_max
    return float(drawdowns.min() * 100)


def compute_sharpe(period_returns: list[float], periods_per_year: float) -> float:
    """
    Sharpe ratio annualized from per-rebalance-period returns.
    periods_per_year: 12 for monthly, 4 for quarterly, 1 for yearly.
    """
    if len(period_returns) < 2:
        return 0.0
    returns = np.array(period_returns)
    mean_excess = returns.mean() - (RISK_FREE_RATE_ANNUAL / periods_per_year)
    std = returns.std(ddof=1)
    if std == 0:
        return 0.0
    return float((mean_excess / std) * np.sqrt(periods_per_year))

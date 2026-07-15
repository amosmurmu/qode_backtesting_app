"""
Orchestration layer between the API route and the pure backtest engine.

Responsibilities:
  1. Pull prices + fundamentals out of Postgres into pandas DataFrames
     (the engine never talks to the DB directly - keeps it testable).
  2. Call the engine.
  3. Convert the engine's raw output into the Pydantic response schema
     the frontend expects (equity curve, drawdown curve, metrics, logs).
"""

from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import Stock, PriceBar, FinancialMetric
from app.schemas.backtest import (
    BacktestRequest,
    BacktestResponse,
    EquityCurvePoint,
    PerformanceMetrics,
    RebalanceLog,
    PortfolioHolding,
    StockReturn,
    RebalanceFrequency,
)
from app.services import backtest_engine as engine

PERIODS_PER_YEAR = {
    RebalanceFrequency.monthly: 12,
    RebalanceFrequency.quarterly: 4,
    RebalanceFrequency.yearly: 1,
}


def _load_prices(db: Session, start: date, end: date) -> pd.DataFrame:
    rows = db.execute(
        select(Stock.ticker, PriceBar.trade_date, PriceBar.adj_close)
        .join(PriceBar, PriceBar.stock_id == Stock.id)
        .where(PriceBar.trade_date >= start, PriceBar.trade_date <= end)
    ).all()
    return pd.DataFrame(rows, columns=["ticker", "trade_date", "adj_close"])


def _load_metrics(db: Session, end: date) -> pd.DataFrame:
    # We pull everything up to `end` - the engine itself enforces the
    # as-of-date cutoff per rebalance, so we just need to not exclude
    # anything it might legitimately need.
    rows = db.execute(
        select(
            Stock.ticker,
            Stock.name,
            FinancialMetric.as_of_date,
            FinancialMetric.market_cap_cr,
            FinancialMetric.pe_ratio,
            FinancialMetric.pb_ratio,
            FinancialMetric.roce_pct,
            FinancialMetric.roe_pct,
            FinancialMetric.revenue_cr,
            FinancialMetric.pat_cr,
            FinancialMetric.operating_margin_pct,
            FinancialMetric.total_debt_cr,
            FinancialMetric.debt_to_equity,
            FinancialMetric.operating_cash_flow_cr,
        )
        .join(FinancialMetric, FinancialMetric.stock_id == Stock.id)
        .where(FinancialMetric.as_of_date <= end)
    ).all()
    columns = [
        "ticker", "name", "as_of_date", "market_cap_cr", "pe_ratio", "pb_ratio",
        "roce_pct", "roe_pct", "revenue_cr", "pat_cr", "operating_margin_pct",
        "total_debt_cr", "debt_to_equity", "operating_cash_flow_cr",
    ]
    return pd.DataFrame(rows, columns=columns)


def _load_benchmark(db: Session, start: date, end: date) -> pd.DataFrame | None:
    """NIFTY 50 is stored as a regular Stock row with ticker '^NSEI'."""
    rows = db.execute(
        select(PriceBar.trade_date, PriceBar.adj_close)
        .join(Stock, Stock.id == PriceBar.stock_id)
        .where(Stock.ticker == "^NSEI", PriceBar.trade_date >= start, PriceBar.trade_date <= end)
    ).all()
    if not rows:
        return None
    return pd.DataFrame(rows, columns=["trade_date", "adj_close"])


def run_backtest_for_request(db: Session, request: BacktestRequest) -> BacktestResponse:
    prices_df = _load_prices(db, request.start_date, request.end_date)
    metrics_df = _load_metrics(db, request.end_date)
    benchmark_df = _load_benchmark(db, request.start_date, request.end_date)

    name_lookup = dict(zip(metrics_df["ticker"], metrics_df["name"])) if not metrics_df.empty else {}

    state = engine.run_backtest(request, prices_df, metrics_df, name_lookup, benchmark_df)

    # ---- Equity curve + drawdown curve ----
    # state.benchmark_curve is built point-for-point alongside state.equity_curve
    # inside the engine, so the two lists are always the same length and the
    # same dates - we zip them directly rather than re-deriving anything here.
    bench_lookup = dict(state.benchmark_curve)
    equity_curve = [
        EquityCurvePoint(
            date=d,
            portfolio_value=round(v, 2),
            benchmark_value=round(bench_lookup.get(d, v), 2) if benchmark_df is not None else None,
        )
        for d, v in state.equity_curve
    ]
    values = [pt.portfolio_value for pt in equity_curve]
    bench_values = [pt.benchmark_value for pt in equity_curve] if benchmark_df is not None else []

    peak = float("-inf")
    bench_peak = float("-inf")
    drawdown_curve = []
    for pt in equity_curve:
        peak = max(peak, pt.portfolio_value)
        dd_pct = ((pt.portfolio_value - peak) / peak * 100) if peak > 0 else 0.0
        bench_dd = None
        if pt.benchmark_value is not None:
            bench_peak = max(bench_peak, pt.benchmark_value)
            bench_dd = ((pt.benchmark_value - bench_peak) / bench_peak * 100) if bench_peak > 0 else 0.0
        drawdown_curve.append(
            EquityCurvePoint(
                date=pt.date,
                portfolio_value=round(dd_pct, 2),
                benchmark_value=round(bench_dd, 2) if bench_dd is not None else None,
            )
        )

    # ---- Headline metrics ----
    years = max((request.end_date - request.start_date).days / 365.25, 1e-6)
    start_val = values[0] if values else request.initial_capital
    end_val = values[-1] if values else request.initial_capital
    cagr = engine.compute_cagr(start_val, end_val, years)
    total_return = ((end_val / start_val) - 1) * 100 if start_val else 0.0
    max_dd = engine.compute_max_drawdown(values)
    periods_per_year = PERIODS_PER_YEAR[request.rebalance_frequency]
    sharpe = engine.compute_sharpe(state.period_returns, periods_per_year)

    pr = np.array(state.period_returns) if state.period_returns else np.array([0.0])
    vol = float(pr.std(ddof=1) * (periods_per_year ** 0.5) * 100) if len(pr) > 1 else 0.0
    win_rate = float((pr > 0).mean() * 100) if len(pr) else 0.0
    best_period = float(pr.max() * 100) if len(pr) else 0.0
    worst_period = float(pr.min() * 100) if len(pr) else 0.0

    benchmark_cagr = None
    benchmark_mdd = None
    if bench_values and bench_values[0]:
        benchmark_cagr = engine.compute_cagr(bench_values[0], bench_values[-1], years)
        benchmark_mdd = engine.compute_max_drawdown(bench_values)

    metrics = PerformanceMetrics(
        cagr_pct=round(cagr, 2),
        total_return_pct=round(total_return, 2),
        annualized_volatility_pct=round(vol, 2),
        sharpe_ratio=round(sharpe, 2),
        max_drawdown_pct=round(max_dd, 2),
        win_rate_pct=round(win_rate, 2),
        best_period_return_pct=round(best_period, 2),
        worst_period_return_pct=round(worst_period, 2),
        benchmark_cagr_pct=round(benchmark_cagr, 2) if benchmark_cagr is not None else None,
        benchmark_max_drawdown_pct=round(benchmark_mdd, 2) if benchmark_mdd is not None else None,
    )

    # ---- Rebalance logs ----
    rebalance_logs = []
    for reb in state.rebalance_history:
        holdings = [
            PortfolioHolding(
                ticker=t,
                name=name_lookup.get(t, t),
                weight=round(w, 4),
                shares=round((reb.portfolio_value_before * w) / reb.entry_prices[t], 4),
                entry_price=round(reb.entry_prices[t], 2),
            )
            for t, w in reb.weights.items()
        ]
        rebalance_logs.append(
            RebalanceLog(
                rebalance_date=reb.rebalance_date,
                portfolio_value=round(reb.portfolio_value_before, 2),
                holdings=holdings,
            )
        )

    # ---- Top winners / losers across the whole backtest ----
    avg_returns = []
    for ticker, rets in state.per_stock_total_return.items():
        compounded = 1.0
        for r in rets:
            compounded *= (1 + r)
        avg_returns.append(
            StockReturn(
                ticker=ticker,
                name=name_lookup.get(ticker, ticker),
                total_return_pct=round((compounded - 1) * 100, 2),
            )
        )
    avg_returns.sort(key=lambda x: x.total_return_pct, reverse=True)
    top_winners = avg_returns[:10]
    top_losers = avg_returns[-10:][::-1] if len(avg_returns) > 10 else avg_returns[::-1]

    return BacktestResponse(
        equity_curve=equity_curve,
        drawdown_curve=drawdown_curve,
        metrics=metrics,
        rebalance_logs=rebalance_logs,
        top_winners=top_winners,
        top_losers=top_losers,
        warnings=state.warnings,
    )

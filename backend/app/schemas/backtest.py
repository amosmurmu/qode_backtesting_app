"""
Pydantic schemas = the "shape" of data crossing the API boundary.

These are NOT database models (that's app/models/). A BacktestRequest is
what the frontend sends us in a POST body; FastAPI validates it
automatically and rejects malformed requests with a clear 422 error before
our code ever runs.
"""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class RebalanceFrequency(str, Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class WeightingMethod(str, Enum):
    equal = "equal"
    market_cap = "market_cap"
    metric = "metric"  # weighted by a chosen fundamental metric, e.g. ROCE


class SortDirection(str, Enum):
    asc = "asc"
    desc = "desc"


class FilterRule(BaseModel):
    """One row of the filtering system, e.g. 'roce_pct > 15'."""

    metric: str = Field(..., description="Column name, e.g. 'roce_pct', 'market_cap_cr', 'pat_cr'")
    operator: str = Field(..., description="One of: '>', '>=', '<', '<=', '==' ")
    value: float


class RankRule(BaseModel):
    """One row of the ranking system, e.g. rank by ROE descending."""

    metric: str
    direction: SortDirection = SortDirection.desc
    # Used for composite ranking: average of multiple ranks, each
    # optionally weighted. Defaults to equal weight across rank rules.
    weight: float = 1.0


class BacktestRequest(BaseModel):
    start_date: date
    end_date: date

    rebalance_frequency: RebalanceFrequency
    portfolio_size: int = Field(..., gt=0, le=50)

    weighting_method: WeightingMethod
    # Only required when weighting_method == metric
    weighting_metric: str | None = None

    filters: list[FilterRule] = Field(default_factory=list)
    rank_rules: list[RankRule] = Field(default_factory=list)

    initial_capital: float = Field(1_000_000, gt=0)

    @model_validator(mode="after")
    def validate_dates_and_weighting(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if self.weighting_method == WeightingMethod.metric and not self.weighting_metric:
            raise ValueError("weighting_metric is required when weighting_method is 'metric'")
        return self


class PortfolioHolding(BaseModel):
    """One stock's position within one rebalance period - for the logs table."""

    ticker: str
    name: str
    weight: float
    shares: float
    entry_price: float
    exit_price: float | None = None
    period_return_pct: float | None = None


class RebalanceLog(BaseModel):
    """One full rebalance event: the date, the chosen portfolio, capital state."""

    rebalance_date: date
    portfolio_value: float
    holdings: list[PortfolioHolding]


class EquityCurvePoint(BaseModel):
    date: date
    portfolio_value: float
    benchmark_value: float | None = None


class PerformanceMetrics(BaseModel):
    cagr_pct: float
    total_return_pct: float
    annualized_volatility_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    best_period_return_pct: float
    worst_period_return_pct: float
    benchmark_cagr_pct: float | None = None
    benchmark_max_drawdown_pct: float | None = None


class StockReturn(BaseModel):
    ticker: str
    name: str
    total_return_pct: float


class BacktestResponse(BaseModel):
    equity_curve: list[EquityCurvePoint]
    drawdown_curve: list[EquityCurvePoint]
    metrics: PerformanceMetrics
    rebalance_logs: list[RebalanceLog]
    top_winners: list[StockReturn]
    top_losers: list[StockReturn]
    warnings: list[str] = Field(default_factory=list)

"""
ORM models = Python classes that mirror database tables.

Three tables, deliberately normalized (per the assignment's requirement):

    stocks              one row per company (static identity info)
    price_bars          one row per (stock, date) - daily OHLCV
    financial_metrics   one row per (stock, period) - fundamentals snapshot

Why split price_bars and financial_metrics into separate tables instead of
one giant table? Prices change daily; fundamentals change quarterly. Mixing
them means massive duplication (repeating the same ROCE 90 times for every
trading day in a quarter) and makes both tables harder to index well.
This is exactly what the assignment asks for: "Separate tables for stock
prices and financial metrics."

See docs/SQLALCHEMY_GUIDE.md for a line-by-line explanation of the syntax
below (Mapped[], mapped_column, relationship, etc.) if SQLAlchemy is new
to you.
"""

from datetime import date, datetime

from sqlalchemy import (
    String,
    Date,
    DateTime,
    Numeric,
    BigInteger,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Stock(Base):
    """
    One row per company. This is the 'identity' table everything else
    points back to via foreign key.
    """

    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Yahoo Finance ticker, e.g. "RELIANCE.NS" - unique and indexed because
    # we look stocks up by ticker constantly (every price fetch, every
    # ranking step).
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # When we last successfully pulled fresh data for this stock - lets the
    # ingestion script skip stocks it already has recent data for.
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # relationship() does NOT create a DB column. It's a Python-side
    # convenience so you can write `my_stock.price_bars` and SQLAlchemy
    # automatically runs the JOIN/SELECT for you.
    price_bars: Mapped[list["PriceBar"]] = relationship(
        back_populates="stock", cascade="all, delete-orphan"
    )
    financial_metrics: Mapped[list["FinancialMetric"]] = relationship(
        back_populates="stock", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Stock {self.ticker}>"


class PriceBar(Base):
    """
    One row = one stock, one trading day, OHLCV.
    This is what the backtester reads to compute returns and equity curves.
    """

    __tablename__ = "price_bars"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)

    trade_date: Mapped[date] = mapped_column(Date, index=True)

    open: Mapped[float] = mapped_column(Numeric(14, 4))
    high: Mapped[float] = mapped_column(Numeric(14, 4))
    low: Mapped[float] = mapped_column(Numeric(14, 4))
    close: Mapped[float] = mapped_column(Numeric(14, 4))
    # "Adjusted close" - close price corrected for splits/dividends.
    # The backtester ALWAYS uses this for return calculations, never raw
    # close, or a stock split would look like a -50% crash.
    adj_close: Mapped[float] = mapped_column(Numeric(14, 4))
    volume: Mapped[int] = mapped_column(BigInteger)

    stock: Mapped["Stock"] = relationship(back_populates="price_bars")

    __table_args__ = (
        # A stock can only have ONE price row per calendar day - this
        # constraint makes that a hard DB-level guarantee, not just an
        # app-level assumption.
        UniqueConstraint("stock_id", "trade_date", name="uq_stock_date"),
        # Composite index: almost every query the backtester runs is
        # "give me this stock's prices between date A and date B", so we
        # index exactly that access pattern for speed.
        Index("ix_price_stock_date", "stock_id", "trade_date"),
    )


class FinancialMetric(Base):
    """
    One row = one stock, one reporting period (e.g. "2025-Q4" or "FY2025").
    Stores everything the filtering/ranking system in the spec needs:
    market cap, ROCE, ROE, PAT, PE, etc.

    We store metrics as nullable floats because real-world fundamental
    data is messy - a newly listed company might not have 5 years of
    history, a bank doesn't report inventory turnover, etc. Forcing
    NOT NULL everywhere would make ingestion brittle.
    """

    __tablename__ = "financial_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)

    # e.g. "2025-Q4" - what reporting period this snapshot belongs to.
    period: Mapped[str] = mapped_column(String(10), index=True)
    # The date this data point becomes valid for backtesting purposes.
    # CRITICAL for avoiding lookahead bias - see "as_of_date" note below.
    as_of_date: Mapped[date] = mapped_column(Date, index=True)

    # --- Valuation / size ---
    market_cap_cr: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    pe_ratio: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    pb_ratio: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # --- Profitability / quality ---
    roce_pct: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    roe_pct: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    # --- P&L items ---
    revenue_cr: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    pat_cr: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    operating_margin_pct: Mapped[float | None] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # --- Balance sheet ---
    total_debt_cr: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    # --- Cash flow ---
    operating_cash_flow_cr: Mapped[float | None] = mapped_column(
        Numeric(18, 2), nullable=True
    )

    stock: Mapped["Stock"] = relationship(back_populates="financial_metrics")

    __table_args__ = (
        UniqueConstraint("stock_id", "period", name="uq_stock_period"),
        Index("ix_metric_stock_asof", "stock_id", "as_of_date"),
    )

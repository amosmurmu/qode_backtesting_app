"""
One-time (or periodic) data ingestion script.

Run with:   uv run python -m app.data.seed_data
       or:  uv run python -m app.data.seed_data --years 5

What it does, per ticker:
  1. Download daily OHLCV history via yfinance -> price_bars table.
  2. Pull yfinance's `.info` dict + quarterly financial statements
     -> derive a handful of FinancialMetric snapshots, one per quarter,
        each stamped with a real `as_of_date` so the backtest engine's
        no-lookahead-bias rule has real dates to work with.
  3. Upsert everything (safe to re-run; won't duplicate rows thanks to
     the UniqueConstraints defined on the models).

This script deliberately fetches one ticker at a time with a short delay
between requests. yfinance hits Yahoo's public endpoints, which will
soft-throttle (or return empty data) if you hammer them - the delay is
cheap insurance against a flaky ingestion run, not a hard requirement.

NOTE: requires real internet access to query{1,2}.finance.yahoo.com.
"""

import argparse
import socket
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.models.stock import Stock, PriceBar, FinancialMetric
from app.data.tickers import NSE_TICKERS, BENCHMARK_TICKER

REQUEST_DELAY_SECONDS = 0.6
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0
YAHOO_HOST = "query1.finance.yahoo.com"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_db_counts(db: Session) -> dict:
    stock_count = db.scalar(select(func.count(Stock.id))) or 0
    price_count = db.scalar(select(func.count(PriceBar.id))) or 0
    metric_count = db.scalar(select(func.count(FinancialMetric.id))) or 0
    earliest = db.scalar(select(func.min(PriceBar.trade_date)))
    latest = db.scalar(select(func.max(PriceBar.trade_date)))
    return {
        "stocks": stock_count,
        "price_rows": price_count,
        "metric_rows": metric_count,
        "price_date_range": [earliest, latest],
    }


def print_db_status(db: Session, label: str = "Database status") -> dict:
    counts = get_db_counts(db)
    date_range = counts["price_date_range"]
    range_text = (
        f"{date_range[0]} → {date_range[1]}"
        if date_range[0] and date_range[1]
        else "no price data"
    )
    print(f"\n--- {label} ---")
    print(f"Stocks:       {counts['stocks']}")
    print(f"Price rows:   {counts['price_rows']}")
    print(f"Metric rows:  {counts['metric_rows']}")
    print(f"Date range:   {range_text}")
    return counts


def check_database() -> Session:
    try:
        db = SessionLocal()
        db.execute(select(func.count(Stock.id)))
        return db
    except OperationalError as e:
        print("\n[error] Cannot connect to the database.")
        print(f"        {e}")
        print("\nFix:")
        print("  1. Start Docker Desktop (Windows) or the Docker daemon")
        print("  2. cd backend && docker compose up -d")
        print("  3. Wait ~10s, then re-run this script")
        print("\nData is stored in PostgreSQL (Docker volume 'qode_pgdata'), not in the browser.")
        print("It persists across reboots once Docker is running again.")
        raise SystemExit(1) from e


def check_network() -> None:
    try:
        socket.getaddrinfo(YAHOO_HOST, 443)
    except socket.gaierror:
        print(f"\n[error] Cannot resolve {YAHOO_HOST} (DNS/network failure).")
        print("yfinance needs internet access to Yahoo Finance.")
        print("\nCommon fixes on WSL2 after a PC restart:")
        print("  1. From Windows PowerShell:  wsl --shutdown")
        print("     Then reopen your WSL terminal")
        print("  2. Check Windows internet/VPN is working")
        print("  3. Retry:  ping query1.finance.yahoo.com")
        print("\nIf you already seeded successfully once, your data may still be in Postgres.")
        print("Run:  uv run python -m app.data.seed_data --status")
        raise SystemExit(1)


def get_or_create_stock(db: Session, ticker: str, name: str, sector: str | None, industry: str | None) -> Stock:
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if stock is None:
        stock = Stock(ticker=ticker, name=name, sector=sector, industry=industry)
        db.add(stock)
        db.flush()  # assigns stock.id without committing the whole transaction yet
    else:
        stock.name = name or stock.name
        stock.sector = sector or stock.sector
        stock.industry = industry or stock.industry
        stock.last_updated = utcnow()
    return stock


def upsert_price_bars(db: Session, stock: Stock, history: pd.DataFrame) -> int:
    """history is the DataFrame returned by yfinance's Ticker.history()."""
    existing_dates = {
        d for (d,) in db.query(PriceBar.trade_date).filter(PriceBar.stock_id == stock.id).all()
    }
    new_rows = 0
    for idx, row in history.iterrows():
        trade_date = idx.date() if hasattr(idx, "date") else idx
        if trade_date in existing_dates:
            continue
        if pd.isna(row.get("Close")):
            continue
        bar = PriceBar(
            stock_id=stock.id,
            trade_date=trade_date,
            open=float(row.get("Open", row["Close"])),
            high=float(row.get("High", row["Close"])),
            low=float(row.get("Low", row["Close"])),
            close=float(row["Close"]),
            adj_close=float(row.get("Close", row["Close"])),  # yfinance auto_adjust=True by default
            volume=int(row.get("Volume", 0) or 0),
        )
        db.add(bar)
        new_rows += 1
    return new_rows


def derive_metric_snapshots(ticker_obj: yf.Ticker, info: dict) -> list[dict]:
    """
    Build a list of fundamental snapshots from yfinance's quarterly
    financial statements. Each snapshot gets an as_of_date roughly 45 days
    after the quarter-end date, approximating real-world reporting lag
    (Indian companies typically report 30-45 days after quarter close) -
    this is exactly what protects the backtest from lookahead bias.
    """
    snapshots = []
    try:
        qfin = ticker_obj.quarterly_financials  # P&L, columns = quarter-end dates
        qbs = ticker_obj.quarterly_balance_sheet
        qcf = ticker_obj.quarterly_cashflow
    except Exception:
        return snapshots

    if qfin is None or qfin.empty:
        return snapshots

    market_cap = info.get("marketCap")
    pe_ratio = info.get("trailingPE")
    pb_ratio = info.get("priceToBook")
    roe = info.get("returnOnEquity")
    debt_to_equity = info.get("debtToEquity")

    for col in qfin.columns:
        quarter_end: date = col.date() if hasattr(col, "date") else col
        as_of = quarter_end + timedelta(days=45)

        def safe_get(df, row_label):
            try:
                if df is not None and row_label in df.index:
                    val = df.loc[row_label, col]
                    return float(val) / 1e7 if pd.notna(val) else None  # paise->Cr scale guard
            except Exception:
                return None
            return None

        revenue = safe_get(qfin, "Total Revenue")
        pat = safe_get(qfin, "Net Income")
        ebit = safe_get(qfin, "EBIT")
        total_debt = safe_get(qbs, "Total Debt")
        op_cash_flow = safe_get(qcf, "Operating Cash Flow")

        roce_pct = None
        if ebit is not None and qbs is not None and "Total Assets" in (qbs.index if qbs is not None else []):
            try:
                total_assets = safe_get(qbs, "Total Assets")
                curr_liab = safe_get(qbs, "Current Liabilities")
                capital_employed = (total_assets or 0) - (curr_liab or 0)
                if capital_employed and capital_employed != 0:
                    roce_pct = round((ebit / capital_employed) * 100, 2)
            except Exception:
                roce_pct = None

        op_margin = None
        if revenue and ebit and revenue != 0:
            op_margin = round((ebit / revenue) * 100, 2)

        snapshots.append(
            {
                "period": f"{quarter_end.year}-Q{(quarter_end.month - 1) // 3 + 1}",
                "as_of_date": as_of,
                "market_cap_cr": round(market_cap / 1e7, 2) if market_cap else None,
                "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
                "pb_ratio": round(pb_ratio, 2) if pb_ratio else None,
                "roce_pct": roce_pct,
                "roe_pct": round(roe * 100, 2) if roe else None,
                "revenue_cr": round(revenue, 2) if revenue is not None else None,
                "pat_cr": round(pat, 2) if pat is not None else None,
                "operating_margin_pct": op_margin,
                "total_debt_cr": round(total_debt, 2) if total_debt is not None else None,
                "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else None,
                "operating_cash_flow_cr": round(op_cash_flow, 2) if op_cash_flow is not None else None,
            }
        )
    return snapshots


def upsert_financial_metrics(db: Session, stock: Stock, snapshots: list[dict]) -> int:
    existing_periods = {
        p for (p,) in db.query(FinancialMetric.period).filter(FinancialMetric.stock_id == stock.id).all()
    }
    new_rows = 0
    for snap in snapshots:
        if snap["period"] in existing_periods:
            continue
        db.add(FinancialMetric(stock_id=stock.id, **snap))
        new_rows += 1
    return new_rows


def ingest_ticker(db: Session, ticker: str, years: int) -> tuple[int, int]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            t = yf.Ticker(ticker)
            info = {}
            try:
                info = t.info or {}
            except Exception as e:
                print(f"  [warn] could not fetch info for {ticker}: {e}")

            name = info.get("longName") or info.get("shortName") or ticker.replace(".NS", "")
            sector = info.get("sector")
            industry = info.get("industry")

            stock = get_or_create_stock(db, ticker, name, sector, industry)

            history = t.history(period=f"{years}y", auto_adjust=True)
            price_rows = upsert_price_bars(db, stock, history) if not history.empty else 0

            snapshots = derive_metric_snapshots(t, info)
            metric_rows = upsert_financial_metrics(db, stock, snapshots)

            db.commit()
            return price_rows, metric_rows
        except Exception as e:
            last_error = e
            db.rollback()
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * attempt
                print(f"  [retry {attempt}/{MAX_RETRIES - 1}] {ticker}: {e} — waiting {wait:.0f}s")
                time.sleep(wait)
            else:
                raise last_error
    raise last_error  # unreachable, keeps type checkers happy


def ingest_benchmark(db: Session, years: int) -> int:
    """NIFTY 50 index - stored as a Stock row too, just with no fundamentals."""
    t = yf.Ticker(BENCHMARK_TICKER)
    stock = get_or_create_stock(db, BENCHMARK_TICKER, "NIFTY 50 Index", "Index", None)
    history = t.history(period=f"{years}y", auto_adjust=True)
    rows = upsert_price_bars(db, stock, history) if not history.empty else 0
    db.commit()
    return rows


def main():
    parser = argparse.ArgumentParser(description="Seed the backtester database from yfinance.")
    parser.add_argument("--years", type=int, default=5, help="Years of price history to fetch")
    parser.add_argument("--limit", type=int, default=None, help="Only ingest the first N tickers (for quick testing)")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Only show what's already in the database (no network fetch)",
    )
    args = parser.parse_args()

    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)

    db = check_database()

    if args.status:
        counts = print_db_status(db, label="Current database contents")
        db.close()
        if counts["price_rows"] == 0:
            print("\nDatabase is empty. Start Docker, fix network, then run without --status.")
            raise SystemExit(1)
        print("\nData is present. Start the API and frontend — no re-seed needed.")
        return

    before = print_db_status(db, label="Before ingestion")
    check_network()

    tickers = NSE_TICKERS[: args.limit] if args.limit else NSE_TICKERS

    print(f"\nIngesting NIFTY 50 benchmark ({args.years}y)...")
    try:
        bench_rows = ingest_benchmark(db, args.years)
        print(f"  -> {bench_rows} new price rows")
    except Exception as e:
        print(f"  [error] benchmark ingestion failed: {e}")

    print(f"Ingesting {len(tickers)} tickers ({args.years}y of price history each)...")
    total_price_rows = 0
    total_metric_rows = 0
    failures = []

    for i, ticker in enumerate(tickers, start=1):
        try:
            price_rows, metric_rows = ingest_ticker(db, ticker, args.years)
            total_price_rows += price_rows
            total_metric_rows += metric_rows
            print(f"[{i}/{len(tickers)}] {ticker}: +{price_rows} prices, +{metric_rows} metric snapshots")
        except Exception as e:
            print(f"[{i}/{len(tickers)}] {ticker}: FAILED - {e}")
            failures.append(ticker)
            db.rollback()
        time.sleep(REQUEST_DELAY_SECONDS)

    after = print_db_status(db, label="After ingestion")
    db.close()

    print("\n--- Ingestion summary ---")
    print(f"New price rows this run:  {total_price_rows}")
    print(f"New metric rows this run: {total_metric_rows}")
    if failures:
        print(f"Failed tickers ({len(failures)}): {', '.join(failures)}")

    if total_price_rows == 0 and total_metric_rows == 0:
        if after["price_rows"] > 0:
            print(
                "\nNo NEW rows added — data was already loaded from a previous successful run."
            )
            print("This is normal. Your backtester should work if the API can reach Postgres.")
        else:
            print("\nNothing was ingested. Check network/DNS errors above and retry.")
            raise SystemExit(1)

    if before["price_rows"] == 0 and after["price_rows"] > 0:
        print("\nFirst-time seed complete. Start the backend API and frontend to backtest.")
    print("Done.")


if __name__ == "__main__":
    main()

"""
API routes. Thin by design - all real logic lives in app/services/.
A route's job is: validate input (Pydantic does this for free), call a
service, return a response.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.stock import Stock, FinancialMetric, PriceBar
from app.schemas.backtest import BacktestRequest, BacktestResponse
from app.services.backtest_service import run_backtest_for_request

router = APIRouter()


@router.post("/backtest", response_model=BacktestResponse)
def run_backtest(request: BacktestRequest, db: Session = Depends(get_db)):
    try:
        return run_backtest_for_request(db, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stocks")
def list_stocks(db: Session = Depends(get_db)):
    """Used by the frontend to show data coverage / available universe."""
    rows = db.execute(select(Stock.ticker, Stock.name, Stock.sector)).all()
    return [{"ticker": r.ticker, "name": r.name, "sector": r.sector} for r in rows]


@router.get("/metrics/available")
def available_metrics():
    """
    Tells the frontend which fundamental columns it can offer in the
    filter/rank builder UI, with human-readable labels.
    """
    return [
        {"key": "market_cap_cr", "label": "Market Cap (₹ Cr)"},
        {"key": "pe_ratio", "label": "PE Ratio"},
        {"key": "pb_ratio", "label": "PB Ratio"},
        {"key": "roce_pct", "label": "ROCE (%)"},
        {"key": "roe_pct", "label": "ROE (%)"},
        {"key": "revenue_cr", "label": "Revenue (₹ Cr)"},
        {"key": "pat_cr", "label": "PAT (₹ Cr)"},
        {"key": "operating_margin_pct", "label": "Operating Margin (%)"},
        {"key": "total_debt_cr", "label": "Total Debt (₹ Cr)"},
        {"key": "debt_to_equity", "label": "Debt to Equity"},
        {"key": "operating_cash_flow_cr", "label": "Operating Cash Flow (₹ Cr)"},
    ]


@router.get("/data-coverage")
def data_coverage(db: Session = Depends(get_db)):
    """Quick sanity-check endpoint: how much data is actually in the DB."""
    stock_count = db.scalar(select(func.count(Stock.id)))
    price_count = db.scalar(select(func.count(PriceBar.id)))
    metric_count = db.scalar(select(func.count(FinancialMetric.id)))
    earliest = db.scalar(select(func.min(PriceBar.trade_date)))
    latest = db.scalar(select(func.max(PriceBar.trade_date)))
    return {
        "stocks": stock_count,
        "price_rows": price_count,
        "metric_rows": metric_count,
        "price_date_range": [earliest, latest],
    }

"""
FastAPI app entrypoint.

Run locally with:  uv run uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import router as backtest_router

settings = get_settings()

app = FastAPI(
    title="Qode Backtester API",
    description="Backend for the equity fundamental strategy backtesting platform.",
    version="0.1.0",
)

# Lets the React dev server (different port = different origin) call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(backtest_router, prefix="/api", tags=["backtest"])


@app.get("/")
def root():
    return {"status": "ok", "service": "qode-backtester-api"}


@app.get("/health")
def health():
    return {"status": "healthy"}

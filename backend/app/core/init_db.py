"""
Creates all tables defined in app/models/ if they don't already exist.

Run: uv run python -m app.core.init_db

You normally don't need to run this separately - app/data/seed_data.py
calls Base.metadata.create_all() automatically before ingesting data.
This script exists for the case where you want to set up the schema
without immediately running the (slow) data ingestion.
"""

from app.core.database import engine, Base
from app.models import stock  # noqa: F401  (import registers the models with Base)


def main():
    print("Creating tables (if they don't already exist)...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables: stocks, price_bars, financial_metrics")


if __name__ == "__main__":
    main()

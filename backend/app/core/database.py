"""
Database engine + session setup.

This is the ONE place SQLAlchemy's `engine` gets created. Everything else
(models, services, API routes) imports `Base` or `get_db` from here -
we never create a second engine.

See docs/SQLALCHEMY_GUIDE.md for a from-scratch explanation of every
concept used in this file (engine, session, declarative base).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# The Engine manages the actual pool of connections to Postgres.
# echo=False keeps logs quiet; flip to True locally if you want to see
# every SQL statement SQLAlchemy generates (great for learning/debugging).
engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)

# A Session is a single "workspace" for a request: it tracks objects you
# load/add/modify and flushes them to the DB in one transaction.
# We create a *factory* (SessionLocal) and build a fresh Session per request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Every ORM model (Stock, PriceBar, FinancialMetric...) inherits this."""

    pass


def get_db():
    """
    FastAPI dependency. Yields one Session per request and guarantees it's
    closed afterwards, even if the request raises an exception.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

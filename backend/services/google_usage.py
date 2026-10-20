"""
Persistent counter of billable Google Places calls, per SKU and month (table google_api_usage).
Replaces the old google_quota.json file, which was wiped by every deploy.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import func
from database import SessionLocal
from models import GoogleApiUsage


def month_key(dt: datetime | None = None) -> str:
    return (dt or datetime.utcnow()).strftime("%Y-%m")


def record_calls(sku: str, calls: int = 1) -> None:
    """Record `calls` billable units of `sku` (one Text Search page = 1, one Place Details = 1)."""
    if calls <= 0:
        return
    db = SessionLocal()
    try:
        db.add(GoogleApiUsage(month_key=month_key(), sku=sku, calls=int(calls)))
        db.commit()
    except Exception:
        db.rollback()        # never break a scrape because the counter failed
    finally:
        db.close()


def get_month_usage(month: str | None = None, db=None) -> dict[str, int]:
    """{sku: calls} for the month ('YYYY-MM', default current UTC month)."""
    own = db is None
    db = db or SessionLocal()
    try:
        rows = (db.query(GoogleApiUsage.sku, func.sum(GoogleApiUsage.calls))
                  .filter(GoogleApiUsage.month_key == (month or month_key()))
                  .group_by(GoogleApiUsage.sku).all())
        return {sku: int(n or 0) for sku, n in rows}
    finally:
        if own:
            db.close()

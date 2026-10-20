"""
Monthly Google Places request counter — now backed by Postgres/SQLite (table google_api_usage)
instead of google_quota.json, so it survives deploys. Kept as a thin compatibility layer for the
"Google Places Quota" pill (GET /api/scraper/google-quota).

Default monthly request budget: 6000. Override with GOOGLE_PLACES_MONTHLY_BUDGET.
Money limits live in routers/google_spend.py (GOOGLE_SPEND_LIMIT_USD / GOOGLE_SPEND_WARN_USD).
"""
import os
from datetime import datetime
from pathlib import Path
import json

from database import SessionLocal
from models import GoogleApiUsage
from services import google_usage, google_pricing

LEGACY_FILE = Path(__file__).resolve().parent.parent / "google_quota.json"
DEFAULT_MONTHLY_BUDGET = 6000


def _monthly_budget() -> int:
    try:
        return int(os.getenv("GOOGLE_PLACES_MONTHLY_BUDGET", DEFAULT_MONTHLY_BUDGET))
    except (ValueError, TypeError):
        return DEFAULT_MONTHLY_BUDGET


def get_status() -> dict:
    used = sum(google_usage.get_month_usage().values())
    limit = _monthly_budget()
    return {"used": used, "limit": limit, "remaining": max(0, limit - used), "month": google_usage.month_key()}


def import_legacy_file() -> int:
    """
    One-time migration of the old google_quota.json (desktop installs; on Railway the file is gone).
    If it belongs to the current month and the table has no usage for this month yet, its count is
    inserted under the scraper's Text Search SKU (the only call the old counter tracked) and the file
    is renamed to *.migrated so it is never imported twice. Returns the number of calls imported.
    """
    if not LEGACY_FILE.exists():
        return 0
    try:
        data = json.loads(LEGACY_FILE.read_text())
        used = int(data.get("used", 0))
        same_month = data.get("month") == google_usage.month_key()
    except Exception:
        return 0
    imported = 0
    db = SessionLocal()
    try:
        if same_month and used > 0 and not db.query(GoogleApiUsage).filter(
                GoogleApiUsage.month_key == google_usage.month_key()).first():
            from services.google_places_service import TEXT_SEARCH_SKU
            db.add(GoogleApiUsage(month_key=google_usage.month_key(), sku=TEXT_SEARCH_SKU, calls=used,
                                  created_at=datetime.utcnow()))
            db.commit()
            imported = used
    finally:
        db.close()
    try:
        LEGACY_FILE.rename(LEGACY_FILE.with_suffix(".json.migrated"))
    except OSError:
        pass
    return imported

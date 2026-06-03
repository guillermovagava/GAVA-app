"""
Tracks monthly Google Places API requests locally.
Resets automatically on the 1st of each month.
Stored in google_quota.json at the backend root.

Default monthly budget: 6000 requests (~$200 free credit at ~$0.032/request).
Override with GOOGLE_PLACES_MONTHLY_BUDGET env var.
"""
import json
import os
from datetime import datetime
from pathlib import Path

QUOTA_FILE = Path(__file__).resolve().parent.parent / "google_quota.json"
DEFAULT_MONTHLY_BUDGET = 6000


def _monthly_budget() -> int:
    try:
        return int(os.getenv("GOOGLE_PLACES_MONTHLY_BUDGET", DEFAULT_MONTHLY_BUDGET))
    except (ValueError, TypeError):
        return DEFAULT_MONTHLY_BUDGET


def _load() -> dict:
    if QUOTA_FILE.exists():
        try:
            return json.loads(QUOTA_FILE.read_text())
        except Exception:
            pass
    return {"month": _current_month(), "used": 0}


def _save(data: dict):
    QUOTA_FILE.write_text(json.dumps(data, indent=2))


def _current_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def get_status() -> dict:
    data = _load()
    if data["month"] != _current_month():
        data = {"month": _current_month(), "used": 0}
        _save(data)
    limit = _monthly_budget()
    remaining = max(0, limit - data["used"])
    return {
        "used":      data["used"],
        "limit":     limit,
        "remaining": remaining,
        "month":     data["month"],
    }


def increment(n: int = 1):
    """Call after each Places API searchText call."""
    if n <= 0:
        return
    data = _load()
    if data["month"] != _current_month():
        data = {"month": _current_month(), "used": 0}
    data["used"] += n
    _save(data)

"""
Tracks monthly Hunter.io usage locally so we never exceed the free tier (25/month).
Resets automatically on the 1st of each month.
Stored in hunter_quota.json next to this file.
"""
import json
import os
from datetime import datetime
from pathlib import Path

QUOTA_FILE = Path(__file__).resolve().parent.parent / "hunter_quota.json"
FREE_TIER_LIMIT = 25  # change to 500 if you upgrade to Hunter Starter


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
    """Returns current usage info."""
    data = _load()
    # Reset if new month
    if data["month"] != _current_month():
        data = {"month": _current_month(), "used": 0}
        _save(data)
    remaining = max(0, FREE_TIER_LIMIT - data["used"])
    return {
        "used":      data["used"],
        "limit":     FREE_TIER_LIMIT,
        "remaining": remaining,
        "month":     data["month"],
        "can_use":   remaining > 0,
    }


def increment():
    """Call this after a successful Hunter.io search."""
    data = _load()
    if data["month"] != _current_month():
        data = {"month": _current_month(), "used": 0}
    data["used"] += 1
    _save(data)


def can_use() -> bool:
    return get_status()["can_use"]

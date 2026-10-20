"""
Spend summary, pre-scrape estimate and spend-limit gate (combines the persistent call counter,
the pricing table and the real billing data).
"""
from __future__ import annotations
import calendar
import math
import os
from datetime import datetime

from sqlalchemy.orm import Session

from services import google_usage, google_pricing, google_billing
from services.google_places_service import TEXT_SEARCH_SKU, PLACE_DETAILS_PER_BUSINESS, TEXT_SEARCH_FIELD_MASK

PAGE_SIZE = 20


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def spend_limit_usd() -> float:
    return _float_env("GOOGLE_SPEND_LIMIT_USD", 10.0)


def spend_warn_usd() -> float:
    return _float_env("GOOGLE_SPEND_WARN_USD", 2.0)


# Calls of jobs that were accepted but have not finished: their calls are not in the counter yet (or only
# partly), and the real billing lags by hours, so without this a loop of /run calls could each pass the gate.
# In-memory on purpose (a restart also kills the background jobs). It is conservative: while a job runs, calls
# already recorded are counted twice.
_inflight: dict[int, dict[str, int]] = {}


def reserve(job_id: int, calls: dict[str, int]) -> None:
    _inflight[job_id] = dict(calls)


def release(job_id: int) -> None:
    _inflight.pop(job_id, None)


def inflight_calls() -> dict[str, int]:
    out: dict[str, int] = {}
    for calls in _inflight.values():
        for sku, n in calls.items():
            out[sku] = out.get(sku, 0) + n
    return out


def scrape_calls(n_locations: int, n_searches: int, max_results_per_city: int) -> dict[str, int]:
    """
    Billable calls of a scrape (upper bound): one Text Search page per 20 results, per location and search.
      text_search = locations × searches × ceil(max_results / 20)
    Place Details: 0 today (the scraper only uses Text Search); one per expected business if that changes.
    """
    pages = max(1, math.ceil(max_results_per_city / PAGE_SIZE))
    ts = n_locations * n_searches * pages
    calls = {TEXT_SEARCH_SKU: ts}
    if PLACE_DETAILS_PER_BUSINESS:
        calls[google_pricing.place_details_sku(TEXT_SEARCH_FIELD_MASK)] = n_locations * n_searches * max_results_per_city
    return calls


def estimate(db: Session, calls: dict[str, int]) -> dict:
    """Pre-run estimate + what the month looks like if it runs."""
    month = google_usage.month_key()
    usage = google_usage.get_month_usage(month, db)
    pending = inflight_calls()
    before = {k: usage.get(k, 0) + pending.get(k, 0) for k in set(usage) | set(pending)}
    est = google_pricing.estimate_cost(before, calls)
    real = google_billing.real_spend(db, month)
    internal = google_pricing.month_cost(before)["total_usd"]
    # Real billing lags by hours and only exists once the export is on; take the larger of the two so a
    # lagging export can never hide spend that the counter already knows about.
    basis = max(real["net_usd"] or 0.0, internal)
    projected = round(basis + est["total_usd"], 4)
    limit, warn = spend_limit_usd(), spend_warn_usd()
    return {
        "calls": calls, "total_usd": est["total_usd"], "breakdown": est["breakdown"],
        "free_remaining": {sku: v for sku, v in google_pricing.free_remaining(before).items()
                           if v["used"] or sku == TEXT_SEARCH_SKU},
        "month": month, "real_net_usd": real["net_usd"], "real_status": real["status"],
        "internal_month_usd": round(internal, 4), "spent_basis_usd": round(basis, 4),
        "projected_month_usd": projected, "limit_usd": limit, "warn_usd": warn,
        "exceeds_limit": projected > limit, "needs_warning": est["total_usd"] > warn,
        "unpriced_skus": [s for s, b in est["breakdown"].items() if not b["priced"]],
    }


def summary(db: Session) -> dict:
    now = datetime.utcnow()
    month = google_usage.month_key(now)
    usage = google_usage.get_month_usage(month, db)
    real = google_billing.real_spend(db, month)
    internal = google_pricing.month_cost(usage)
    days_in_month, elapsed = calendar.monthrange(now.year, now.month)[1], max(1, now.day)
    basis_kind = "real" if real["status"] == "ok" and real["net_usd"] is not None else "internal"
    basis_usd = real["net_usd"] if basis_kind == "real" else internal["total_usd"]
    daily = basis_usd / elapsed
    return {
        "month": month,
        "real": real,
        "internal": {"calls_by_sku": usage, "estimated_usd": internal["total_usd"], "breakdown": internal["breakdown"],
                     "unpriced_skus": [s for s, b in internal["breakdown"].items() if not b["priced"]]},
        "free_remaining": {sku: v for sku, v in google_pricing.free_remaining(usage).items()
                           if v["used"] or sku == TEXT_SEARCH_SKU},
        "scraper_sku": TEXT_SEARCH_SKU,
        "projection": {"basis": basis_kind, "daily_avg_usd": round(daily, 4), "days_elapsed": elapsed,
                       "days_in_month": days_in_month, "projected_usd": round(daily * days_in_month, 4)},
        "limit_usd": spend_limit_usd(), "warn_usd": spend_warn_usd(),
        "last_sync_at": real["last_sync_at"], "billing_configured": google_billing.is_configured(),
        "prices_as_of": google_pricing.PRICES_AS_OF,
    }

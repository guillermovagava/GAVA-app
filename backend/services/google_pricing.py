"""
Google Maps Platform (Places API New) pricing — single source of truth.

Prices copied from https://developers.google.com/maps/billing-and-pricing/pricing
PRICES_AS_OF = 2026-10-16. To update prices, edit ONLY the SKUS table below (and PRICES_AS_OF).

How billing works (and how estimate_cost models it)
───────────────────────────────────────────────────
* Each SKU has a monthly free cap (free_cap). The free cap is consumed ONCE per month per SKU,
  not once per scrape run.
* Above the free cap, calls are priced by volume tier. `tiers` is a list of
  (upper_bound, usd_per_1000), where upper_bound is the cumulative number of BILLABLE calls
  (calls above the free cap) in the month, and None means "no upper bound".
  ASSUMPTION: tier boundaries count billable calls (after the free cap). The tiers only matter
  beyond 100k billable calls/month, far above this app's usage.
* The price of a call depends on the TOTAL usage of the month, not on the run that makes it,
  so the cost of a run is  cost(usage_before + new) − cost(usage_before).

Field mask → SKU (Text Search, Places API New)
──────────────────────────────────────────────
Text Search is billed by the HIGHEST field tier requested in X-Goog-FieldMask:
  • IDs Only      : the mask asks only for places.id / places.name (+ nextPageToken)
  • Pro           : id, displayName, formattedAddress, location, photos, types, addressComponents,
                    businessStatus, googleMapsUri, ...
  • Enterprise    : contact and rating data — nationalPhoneNumber, internationalPhoneNumber,
                    websiteUri, regularOpeningHours / currentOpeningHours, rating, userRatingCount,
                    priceLevel, priceRange
  • Enterprise + Atmosphere : reviews, editorialSummary, generativeSummary, reviewSummary and the
                    amenity flags (dineIn, takeout, delivery, outdoorSeating, ...)
So asking for phone/website (as the scraper does) → Enterprise; adding hours or contact keeps it at
Enterprise; adding reviews moves it to Enterprise + Atmosphere. Place Details has the same tiers
(Essentials / Pro / Enterprise / Enterprise + Atmosphere) with its own SKUs.
Fields not listed in the sets below are treated as Pro (unknown fields never lower the tier;
see classify_field_mask) — check the pricing page when adding fields.
"""
from __future__ import annotations

PRICES_AS_OF = "2026-10-16"

# ── SKU names (exactly as they appear in Cloud Billing's sku.description, minus any region suffix) ──
TEXT_SEARCH_IDS_ONLY = "Places API Text Search Essentials (IDs Only)"
TEXT_SEARCH_PRO = "Places API Text Search Pro"
TEXT_SEARCH_ENTERPRISE = "Places API Text Search Enterprise"
TEXT_SEARCH_ENTERPRISE_ATMOSPHERE = "Places API Text Search Enterprise + Atmosphere"  # no price configured yet
NEARBY_SEARCH_PRO = "Places API Nearby Search Pro"
DETAILS_ESSENTIALS = "Places API Place Details Essentials"
DETAILS_PRO = "Places API Place Details Pro"
DETAILS_ENTERPRISE = "Places API Place Details Enterprise"
DETAILS_ENTERPRISE_ATMOSPHERE = "Places API Place Details Enterprise + Atmosphere"
DETAILS_PHOTOS = "Places API Place Details Photos"   # GET /v1/{photo}/media — used by /api/leads/{id}/photo

_PRO_TIERS = [(100_000, 32.00), (500_000, 25.60), (1_000_000, 19.20), (5_000_000, 9.60), (None, 2.40)]

# sku → {"free_cap": int | None (None = unlimited free), "tiers": [(upper_bound | None, usd_per_1000)], "tier": field tier}
SKUS: dict[str, dict] = {
    TEXT_SEARCH_IDS_ONLY: {"free_cap": None, "tiers": [(None, 0.0)], "tier": "ids_only"},
    TEXT_SEARCH_PRO: {"free_cap": 5_000, "tiers": _PRO_TIERS, "tier": "pro"},
    TEXT_SEARCH_ENTERPRISE: {
        "free_cap": 1_000,
        # Only the first tier was provided; higher tiers (>100k billable/month) are not configured.
        "tiers": [(None, 35.00)],
        "tier": "enterprise",
    },
    NEARBY_SEARCH_PRO: {"free_cap": 5_000, "tiers": [(None, 32.00)], "tier": "pro"},
    DETAILS_ESSENTIALS: {"free_cap": 10_000, "tiers": [(None, 5.00)], "tier": "essentials"},
    DETAILS_PRO: {
        "free_cap": 5_000,
        "tiers": [(100_000, 17.00), (500_000, 13.60), (1_000_000, 10.20), (5_000_000, 5.10), (None, 1.28)],
        "tier": "pro",
    },
    DETAILS_ENTERPRISE: {
        "free_cap": 1_000,
        "tiers": [(100_000, 20.00), (500_000, 16.00), (1_000_000, 12.00), (5_000_000, 6.00), (None, 1.51)],
        "tier": "enterprise",
    },
    DETAILS_ENTERPRISE_ATMOSPHERE: {
        "free_cap": 1_000,
        "tiers": [(100_000, 25.00), (500_000, 20.00), (1_000_000, 15.00), (5_000_000, 7.50), (None, 2.28)],
        "tier": "enterprise_atmosphere",
    },
    # Not in the 2026-10-16 spec list; first tier only — verify on the pricing page.
    DETAILS_PHOTOS: {"free_cap": 1_000, "tiers": [(None, 7.00)], "tier": "enterprise"},
}

# ── Field mask → tier ────────────────────────────────────────────────────────────────────────────
_IDS_ONLY_FIELDS = {"id", "name", "nextPageToken"}
_ENTERPRISE_FIELDS = {
    "nationalPhoneNumber", "internationalPhoneNumber", "websiteUri", "regularOpeningHours",
    "currentOpeningHours", "regularSecondaryOpeningHours", "currentSecondaryOpeningHours",
    "rating", "userRatingCount", "priceLevel", "priceRange",
}
_ATMOSPHERE_FIELDS = {
    "reviews", "editorialSummary", "generativeSummary", "reviewSummary", "neighborhoodSummary",
    "delivery", "dineIn", "takeout", "curbsidePickup", "reservable", "outdoorSeating", "liveMusic",
    "servesBreakfast", "servesBrunch", "servesLunch", "servesDinner", "servesBeer", "servesWine",
    "servesCocktails", "servesCoffee", "servesDessert", "servesVegetarianFood", "menuForChildren",
    "goodForChildren", "goodForGroups", "goodForWatchingSports", "allowsDogs", "restroom",
}


def _field_names(field_mask: str) -> set[str]:
    out = set()
    for f in field_mask.split(","):
        f = f.strip()
        if f:
            out.add(f.split(".", 1)[1] if f.startswith("places.") else f)   # "places.websiteUri" → "websiteUri"
    return out


def classify_field_mask(field_mask: str) -> str:
    """Returns 'ids_only' | 'pro' | 'enterprise' | 'enterprise_atmosphere' for a Places (New) field mask."""
    names = _field_names(field_mask)
    if names & _ATMOSPHERE_FIELDS:
        return "enterprise_atmosphere"
    if names & _ENTERPRISE_FIELDS:
        return "enterprise"
    if names and names <= _IDS_ONLY_FIELDS:
        return "ids_only"
    return "pro"


_TEXT_SEARCH_BY_TIER = {
    "ids_only": TEXT_SEARCH_IDS_ONLY, "pro": TEXT_SEARCH_PRO, "enterprise": TEXT_SEARCH_ENTERPRISE,
    "enterprise_atmosphere": TEXT_SEARCH_ENTERPRISE_ATMOSPHERE,
}
_DETAILS_BY_TIER = {
    "ids_only": DETAILS_ESSENTIALS, "pro": DETAILS_PRO, "enterprise": DETAILS_ENTERPRISE,
    "enterprise_atmosphere": DETAILS_ENTERPRISE_ATMOSPHERE,
}


def text_search_sku(field_mask: str) -> str:
    """SKU billed for a Text Search call with this field mask."""
    return _TEXT_SEARCH_BY_TIER[classify_field_mask(field_mask)]


def place_details_sku(field_mask: str) -> str:
    """SKU billed for a Place Details call with this field mask."""
    return _DETAILS_BY_TIER[classify_field_mask(field_mask)]


# ── Cost model ───────────────────────────────────────────────────────────────────────────────────
def normalize_sku(description: str) -> str:
    """Maps a Cloud Billing sku.description (which may carry a region suffix) to a known SKU key."""
    d = (description or "").strip()
    if d in SKUS:
        return d
    known = set(SKUS) | {TEXT_SEARCH_ENTERPRISE_ATMOSPHERE}   # the unpriced one must still win over its shorter prefix
    for name in sorted(known, key=len, reverse=True):     # longest first: "…Enterprise + Atmosphere" before "…Enterprise"
        if d.startswith(name):
            return name
    return d


def _cumulative_cost(sku: str, total_calls: int) -> float:
    """USD charged for `total_calls` cumulative calls of `sku` in one month (free cap + tiers applied)."""
    spec = SKUS[sku]
    billable = max(0, total_calls - (spec["free_cap"] or 0))
    cost, prev_bound = 0.0, 0
    for upper, per_1000 in spec["tiers"]:
        if billable <= prev_bound:
            break
        top = billable if upper is None else min(billable, upper)
        cost += (top - prev_bound) / 1000 * per_1000
        if upper is None:
            break
        prev_bound = upper
    return cost


def free_remaining(usage: dict[str, int]) -> dict[str, dict]:
    """Free monthly calls left per priced SKU, given the month's usage."""
    out = {}
    for sku, spec in SKUS.items():
        used = int(usage.get(sku, 0))
        cap = spec["free_cap"]
        out[sku] = {"free_cap": cap, "used": used, "free_remaining": None if cap is None else max(0, cap - used)}
    return out


def estimate_cost(usage_before: dict[str, int], new_calls: dict[str, int]) -> dict:
    """
    Cost of `new_calls` given the calls already made this month (`usage_before`), per SKU:
    cost = cumulative_cost(before + new) − cumulative_cost(before).
    SKUs without a configured price are reported with priced=False and cost 0 (never silently priced).
    Returns {"total_usd", "breakdown": {sku: {...}}}.
    """
    breakdown: dict[str, dict] = {}
    total = 0.0
    for sku, n in new_calls.items():
        n = int(n)
        if n <= 0:
            continue
        before = int(usage_before.get(sku, 0))
        if sku not in SKUS:
            breakdown[sku] = {"calls": n, "calls_before": before, "free_remaining_before": None,
                              "free_calls": 0, "billable_calls": 0, "cost_usd": 0.0, "priced": False}
            continue
        cap = SKUS[sku]["free_cap"]
        free_before = None if cap is None else max(0, cap - before)
        free_used = n if free_before is None else min(n, free_before)
        cost = _cumulative_cost(sku, before + n) - _cumulative_cost(sku, before)
        total += cost
        breakdown[sku] = {"calls": n, "calls_before": before, "free_remaining_before": free_before,
                          "free_calls": free_used, "billable_calls": n - free_used,
                          "cost_usd": round(cost, 4), "priced": True}
    return {"total_usd": round(total, 4), "breakdown": breakdown}


def month_cost(usage: dict[str, int]) -> dict:
    """Estimated cost of a whole month's usage from zero (same shape as estimate_cost)."""
    return estimate_cost({}, usage)

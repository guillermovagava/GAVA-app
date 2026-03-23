"""
Google Places API (New) — finds businesses then enriches with HR emails.
Hunter.io credits are budgeted per job so you never spend more than you choose.
"""
import os
import asyncio
import httpx
from services.hunter_service import find_hr_contact as hunter_find
from services.web_scraper import find_hr_email as scrape_find

PLACES_NEW_BASE = "https://places.googleapis.com/v1"

GOOGLE_CATEGORIES = [
    {"label": "Hotels & Resorts",        "query": "hotels"},
    {"label": "Resorts",                 "query": "resort"},
    {"label": "Ski Resorts",             "query": "ski resort"},
    {"label": "Amusement Parks",         "query": "amusement park"},
    {"label": "Water Parks",             "query": "water park"},
    {"label": "Campgrounds",             "query": "campground camping"},
    {"label": "Golf & Country Clubs",    "query": "golf course country club"},
    {"label": "Event Venues",            "query": "event venue banquet hall"},
    {"label": "Summer Camps",            "query": "summer camp"},
    {"label": "Vacation Lodges",         "query": "vacation rental lodge"},
    {"label": "Beach Clubs",             "query": "beach club resort"},
    {"label": "Theme Parks",             "query": "theme park"},
]


async def _find_email(
    website: str | None,
    hunter_budget: int,
    hunter_used: list,          # list with one int — acts as mutable counter
) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Returns (email, contact_name, position, email_source).
    email_source = "hunter" | "scraper" | None
    Uses Hunter.io only if budget allows, otherwise falls back to free web scraper.
    hunter_used[0] is incremented each time Hunter.io is called.
    """
    if not website:
        return None, None, None, None

    # Use Hunter.io only if key is set AND we still have budget for this job
    if os.getenv("HUNTER_API_KEY") and hunter_used[0] < hunter_budget:
        result = await hunter_find(website)
        if result.get("email"):
            hunter_used[0] += 1
            return result["email"], result.get("contact_name"), result.get("position"), "hunter"

    # Free fallback — no credit used
    email = await scrape_find(website)
    return email, None, None, ("scraper" if email else None)


async def search_businesses(
    query: str,
    location: str,
    max_results: int = 20,
    hunter_budget: int = 5,
    hunter_used: list | None = None,
) -> list[dict]:
    """
    Search Google Places (New API) for businesses and enrich with contact info.
    hunter_budget = max Hunter.io credits to spend across ALL calls sharing hunter_used.
    """
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        return []

    if hunter_used is None:
        hunter_used = [0]

    results: list[dict] = []
    next_page_token: str | None = None

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.location,"
            "places.nationalPhoneNumber,"
            "places.websiteUri,"
            "nextPageToken"
        ),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        while len(results) < max_results:
            body: dict = {
                "textQuery": f"{query} in {location}",
                "pageSize": min(20, max_results - len(results)),
                "languageCode": "en",
            }
            if next_page_token:
                body["pageToken"] = next_page_token

            try:
                resp = await client.post(
                    f"{PLACES_NEW_BASE}/places:searchText",
                    headers=headers,
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                break

            places = data.get("places", [])[:max_results - len(results)]

            # Enrich all places in this page concurrently — much faster
            async def enrich(place):
                website = place.get("websiteUri")
                phone   = place.get("nationalPhoneNumber")
                addr    = place.get("formattedAddress", "")
                name    = place.get("displayName", {}).get("text", "")
                loc     = place.get("location", {})
                city, state, country = _parse_address(addr)
                email, contact_name, position, email_source = await _find_email(
                    website, hunter_budget, hunter_used
                )
                return {
                    "business_name": name,
                    "category":      query,
                    "phone":         phone,
                    "website":       website,
                    "email":         email,
                    "contact_name":  contact_name,
                    "email_source":  email_source,
                    "address":       addr,
                    "city":          city,
                    "state":         state,
                    "country":       country,
                    "lat":           loc.get("latitude"),
                    "lng":           loc.get("longitude"),
                    "source":        "google",
                }

            enriched = await asyncio.gather(*[enrich(p) for p in places])
            results.extend(enriched)

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
            await asyncio.sleep(2)

    return results


def _parse_address(addr: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in addr.split(",")]
    city, state, country = "", "", "US"
    if parts:
        city = parts[0]
    if len(parts) >= 2:
        state = parts[1].strip().split()[0]
    if "Canada" in addr:
        country = "CA"
    return city, state, country

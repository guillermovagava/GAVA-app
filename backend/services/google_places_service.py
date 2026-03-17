"""
Google Places API scraper.
Finds businesses via Text Search + Place Details, then enriches each
result with an HR email using Hunter.io (if configured) or the free
web scraper as a fallback.
"""
import os
import asyncio
import httpx
from services.hunter_service import find_hr_contact as hunter_find
from services.web_scraper import find_hr_email as scrape_find

PLACES_BASE = "https://maps.googleapis.com/maps/api/place"

GOOGLE_CATEGORIES = [
    {"label": "Hotels & Resorts",  "query": "hotels"},
    {"label": "Resorts",           "query": "resort"},
    {"label": "Ski Resorts",       "query": "ski resort"},
    {"label": "Amusement Parks",   "query": "amusement park"},
    {"label": "Water Parks",       "query": "water park"},
    {"label": "Campgrounds",       "query": "campground camping"},
    {"label": "Golf & Country Clubs", "query": "golf course country club"},
    {"label": "Event Venues",      "query": "event venue banquet hall"},
    {"label": "Summer Camps",      "query": "summer camp"},
    {"label": "Vacation Lodges",   "query": "vacation rental lodge"},
    {"label": "Beach Clubs",       "query": "beach club resort"},
    {"label": "Theme Parks",       "query": "theme park"},
]

_hunter_configured = bool(os.getenv("HUNTER_API_KEY"))


async def _find_email(website: str | None) -> tuple[str | None, str | None, str | None]:
    """
    Returns (email, contact_name, position).
    Tries Hunter.io first (uses 1 credit), falls back to free web scraper.
    """
    if not website:
        return None, None, None

    if os.getenv("HUNTER_API_KEY"):
        result = await hunter_find(website)
        if result.get("email"):
            return result["email"], result.get("contact_name"), result.get("position")

    # Free fallback: crawl the website
    email = await scrape_find(website)
    return email, None, None


async def search_businesses(query: str, location: str, max_results: int = 20) -> list[dict]:
    """Search Google Places and enrich each result with contact info."""
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        return []

    results: list[dict] = []
    next_page_token: str | None = None

    async with httpx.AsyncClient(timeout=15) as client:
        while len(results) < max_results:
            params: dict = {"query": f"{query} in {location}", "key": api_key}
            if next_page_token:
                params = {"pagetoken": next_page_token, "key": api_key}

            try:
                resp = await client.get(f"{PLACES_BASE}/textsearch/json", params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                break

            for place in data.get("results", []):
                if len(results) >= max_results:
                    break
                detail = await _get_details(client, place["place_id"], api_key)
                website = detail.get("website")
                email, contact_name, position = await _find_email(website)

                addr = place.get("formatted_address", "")
                city, state, country = _parse_address(addr)

                results.append({
                    "business_name": place.get("name"),
                    "category":      query,
                    "phone":         detail.get("formatted_phone_number"),
                    "website":       website,
                    "email":         email,
                    "contact_name":  contact_name,
                    "address":       addr,
                    "city":          city,
                    "state":         state,
                    "country":       country,
                    "lat":           place.get("geometry", {}).get("location", {}).get("lat"),
                    "lng":           place.get("geometry", {}).get("location", {}).get("lng"),
                    "source":        "google",
                })

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break
            await asyncio.sleep(2)  # Google requires a delay before using next_page_token

    return results


async def _get_details(client: httpx.AsyncClient, place_id: str, api_key: str) -> dict:
    try:
        resp = await client.get(
            f"{PLACES_BASE}/details/json",
            params={
                "place_id": place_id,
                "fields":   "formatted_phone_number,website",
                "key":      api_key,
            }
        )
        resp.raise_for_status()
        return resp.json().get("result", {})
    except Exception:
        return {}


def _parse_address(addr: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in addr.split(",")]
    country = "US"
    state, city = "", ""
    if parts:
        city = parts[0]
    if len(parts) >= 2:
        state = parts[1].strip().split()[0]
    if len(parts) >= 3 and ("Canada" in parts[-1] or parts[-1].strip() in ("CA", "Canada")):
        country = "CA"
    return city, state, country

"""
Google Places API (New) integration.
Uses the next-generation Places API (200M+ places, more accurate data).
Docs: https://developers.google.com/maps/documentation/places/web-service/text-search

Flow per business found:
  1. Text Search  → list of matching places
  2. Place Details → phone + website
  3. Hunter.io or free web scraper → HR email + contact name
"""
import os
import asyncio
import httpx
from services.hunter_service import find_hr_contact as hunter_find
from services.web_scraper import find_hr_email as scrape_find

# New Places API base (v1)
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


async def _find_email(website: str | None) -> tuple[str | None, str | None, str | None]:
    """
    Returns (email, contact_name, position).
    Tries Hunter.io first (1 credit), falls back to free web scraper.
    """
    if not website:
        return None, None, None

    if os.getenv("HUNTER_API_KEY"):
        result = await hunter_find(website)
        if result.get("email"):
            return result["email"], result.get("contact_name"), result.get("position")

    email = await scrape_find(website)
    return email, None, None


async def search_businesses(query: str, location: str, max_results: int = 20) -> list[dict]:
    """
    Search Places API (New) for businesses matching `query` in `location`.
    Returns a list of enriched lead dicts ready to store in the database.
    """
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        return []

    results: list[dict] = []
    next_page_token: str | None = None

    # Headers required by the New Places API
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        # Fields we want back from Text Search
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

            for place in data.get("places", []):
                if len(results) >= max_results:
                    break

                website = place.get("websiteUri")
                phone   = place.get("nationalPhoneNumber")
                addr    = place.get("formattedAddress", "")
                name    = place.get("displayName", {}).get("text", "")
                loc     = place.get("location", {})
                lat     = loc.get("latitude")
                lng     = loc.get("longitude")

                city, state, country = _parse_address(addr)
                email, contact_name, position = await _find_email(website)

                results.append({
                    "business_name": name,
                    "category":      query,
                    "phone":         phone,
                    "website":       website,
                    "email":         email,
                    "contact_name":  contact_name,
                    "address":       addr,
                    "city":          city,
                    "state":         state,
                    "country":       country,
                    "lat":           lat,
                    "lng":           lng,
                    "source":        "google",
                })

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
            await asyncio.sleep(2)  # brief pause between pages

    return results


def _parse_address(addr: str) -> tuple[str, str, str]:
    """Best-effort city/state/country extraction from a formatted address."""
    parts = [p.strip() for p in addr.split(",")]
    city, state, country = "", "", "US"
    if parts:
        city = parts[0]
    if len(parts) >= 2:
        state = parts[1].strip().split()[0]
    if len(parts) >= 1 and ("Canada" in addr or "Canada" in parts[-1]):
        country = "CA"
    return city, state, country

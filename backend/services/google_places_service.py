"""
Google Places API scraper.
Uses the Text Search + Place Details endpoints to find businesses
and enrich them with phone, website, and coordinates.
"""
import os
import httpx
from typing import Optional
from services.web_scraper import find_hr_email

PLACES_BASE = "https://maps.googleapis.com/maps/api/place"

# Business types mapped to Google Places query keywords
GOOGLE_CATEGORIES = [
    {"label": "Hotels & Resorts",    "query": "hotels"},
    {"label": "Resorts",             "query": "resort"},
    {"label": "Ski Resorts",         "query": "ski resort"},
    {"label": "Amusement Parks",     "query": "amusement park"},
    {"label": "Water Parks",         "query": "water park"},
    {"label": "Campgrounds",         "query": "campground camping"},
    {"label": "Golf Courses",        "query": "golf course country club"},
    {"label": "Event Venues",        "query": "event venue banquet hall"},
    {"label": "Summer Camps",        "query": "summer camp"},
    {"label": "Vacation Rentals",    "query": "vacation rental lodge"},
    {"label": "Beach Clubs",         "query": "beach club resort"},
    {"label": "Theme Parks",         "query": "theme park"},
]


async def search_businesses(query: str, location: str, max_results: int = 20) -> list[dict]:
    """
    Search Google Places for businesses matching `query` near `location`.
    Returns enriched lead dicts ready to insert into the DB.
    """
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        return []

    results: list[dict] = []
    next_page_token: Optional[str] = None

    async with httpx.AsyncClient(timeout=15) as client:
        while len(results) < max_results:
            params: dict = {
                "query": f"{query} in {location}",
                "key": api_key,
            }
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
                email = await find_hr_email(website) if website else None

                addr = place.get("formatted_address", "")
                city, state, country = _parse_address(addr)

                results.append({
                    "business_name": place.get("name"),
                    "category": query,
                    "phone": detail.get("formatted_phone_number"),
                    "website": website,
                    "email": email,
                    "address": addr,
                    "city": city,
                    "state": state,
                    "country": country,
                    "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": place.get("geometry", {}).get("location", {}).get("lng"),
                    "source": "google",
                })

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break
            # Google requires a short delay before using next_page_token
            import asyncio
            await asyncio.sleep(2)

    return results


async def _get_details(client: httpx.AsyncClient, place_id: str, api_key: str) -> dict:
    try:
        resp = await client.get(
            f"{PLACES_BASE}/details/json",
            params={
                "place_id": place_id,
                "fields": "formatted_phone_number,website",
                "key": api_key,
            }
        )
        resp.raise_for_status()
        return resp.json().get("result", {})
    except Exception:
        return {}


def _parse_address(formatted_address: str) -> tuple[str, str, str]:
    """Best-effort parse of 'City, State ZIP, Country' format."""
    parts = [p.strip() for p in formatted_address.split(",")]
    country = "US"
    state = ""
    city = ""
    if len(parts) >= 1:
        city = parts[0]
    if len(parts) >= 2:
        # "FL 33101" or "FL" — grab just the state code
        state_zip = parts[1].strip().split()
        state = state_zip[0] if state_zip else ""
    if len(parts) >= 3:
        country_raw = parts[-1].strip()
        if "Canada" in country_raw or country_raw == "CA":
            country = "CA"
    return city, state, country

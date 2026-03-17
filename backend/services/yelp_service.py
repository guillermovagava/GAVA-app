"""
Yelp Fusion API scraper.
Searches for businesses by category and location, then attempts to discover
HR/recruitment emails by crawling each business website.
"""
import os
import httpx
from typing import Optional
from services.web_scraper import find_hr_email

YELP_API_BASE = "https://api.yelp.com/v3"

# Business categories most relevant to seasonal staffing
SEASONAL_CATEGORIES = [
    {"label": "Hotels & Resorts", "yelp": "hotels"},
    {"label": "Resorts", "yelp": "resorts"},
    {"label": "Ski Resorts", "yelp": "skiresorts"},
    {"label": "Amusement Parks", "yelp": "amusementparks"},
    {"label": "Water Parks", "yelp": "waterparks"},
    {"label": "Campgrounds", "yelp": "campgrounds"},
    {"label": "Golf Courses", "yelp": "golf"},
    {"label": "Country Clubs", "yelp": "countryclubs"},
    {"label": "Event Venues", "yelp": "eventservices"},
    {"label": "Summer Camps", "yelp": "summer_camps"},
    {"label": "Vacation Rentals", "yelp": "vacation_rentals"},
    {"label": "Restaurants (Chain)", "yelp": "restaurants"},
    {"label": "Beach Clubs", "yelp": "beachbars"},
]


async def search_businesses(category_yelp: str, location: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Query Yelp for businesses and enrich with email discovery."""
    api_key = os.getenv("YELP_API_KEY", "")
    if not api_key:
        return []

    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "categories": category_yelp,
        "location": location,
        "limit": min(limit, 50),
        "offset": offset,
        "sort_by": "rating",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(f"{YELP_API_BASE}/businesses/search", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

    businesses = data.get("businesses", [])
    results = []

    for biz in businesses:
        coords = biz.get("coordinates", {})
        location_data = biz.get("location", {})
        categories = [c.get("title", "") for c in biz.get("categories", [])]
        website = await _get_website(biz["id"], headers)
        email = await find_hr_email(website) if website else None

        results.append({
            "yelp_id": biz.get("id"),
            "business_name": biz.get("name"),
            "category": ", ".join(categories) or category_yelp,
            "phone": biz.get("display_phone") or biz.get("phone"),
            "website": website,
            "email": email,
            "address": ", ".join(filter(None, [
                location_data.get("address1"),
                location_data.get("address2"),
            ])),
            "city": location_data.get("city"),
            "state": location_data.get("state"),
            "country": location_data.get("country", "US"),
            "lat": coords.get("latitude"),
            "lng": coords.get("longitude"),
            "source": "yelp",
        })

    return results


async def _get_website(yelp_id: str, headers: dict) -> Optional[str]:
    """Fetch the business detail page to get website URL."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{YELP_API_BASE}/businesses/{yelp_id}", headers=headers)
            resp.raise_for_status()
            return resp.json().get("url") or resp.json().get("website") or None
        except Exception:
            return None

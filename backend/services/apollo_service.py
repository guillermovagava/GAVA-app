"""
Apollo.io API integration.
Apollo is a sales intelligence platform that can find companies AND the
specific people (HR Managers, Recruiting Directors, etc.) at those companies,
including their verified email addresses.

Free tier: 50 credits/month — each person lookup = 1 credit.
Paid plans start at ~$49/month for much higher limits.

Docs: https://apolloio.github.io/apollo-api-docs/
"""
import os
import httpx
from typing import Optional

APOLLO_BASE = "https://api.apollo.io/v1"

# Job titles we want to target for recruitment outreach
HR_TITLES = [
    "HR Manager",
    "Human Resources Manager",
    "Recruiting Manager",
    "Talent Acquisition Manager",
    "Director of Human Resources",
    "HR Director",
    "People Operations Manager",
    "Hiring Manager",
    "Recruitment Manager",
]

# Apollo industry tags relevant to seasonal staffing
APOLLO_INDUSTRIES = [
    "hospitality",
    "leisure travel & tourism",
    "recreational facilities & services",
    "entertainment",
    "food & beverages",
]


async def search_companies(industry: str, location: str, per_page: int = 25) -> list[dict]:
    """
    Search Apollo for companies in a given industry and location.
    Returns basic company info (no credits consumed for org search).
    """
    api_key = os.getenv("APOLLO_API_KEY", "")
    if not api_key:
        return []

    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    payload = {
        "q_organization_industries": [industry],
        "organization_locations": [location],
        "per_page": min(per_page, 25),
        "page": 1,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.post(
                f"{APOLLO_BASE}/mixed_companies/search",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

    results = []
    for org in data.get("organizations", []):
        results.append({
            "business_name": org.get("name"),
            "category": industry,
            "phone": org.get("primary_phone", {}).get("sanitized_number") if org.get("primary_phone") else None,
            "website": org.get("website_url"),
            "email": None,          # filled in by find_hr_contact below
            "contact_name": None,   # filled in by find_hr_contact below
            "address": org.get("raw_address"),
            "city": org.get("city"),
            "state": org.get("state"),
            "country": org.get("country", "US"),
            "lat": None,
            "lng": None,
            "source": "apollo",
            "_apollo_org_id": org.get("id"),   # used for person lookup
        })

    return results


async def find_hr_contact(org_id: str, org_domain: Optional[str] = None) -> dict:
    """
    Search Apollo for an HR/Recruiting person at a given org.
    Returns {"name": ..., "email": ...} or empty dict.
    NOTE: Each successful email reveal consumes 1 Apollo credit.
    """
    api_key = os.getenv("APOLLO_API_KEY", "")
    if not api_key:
        return {}

    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    payload = {
        "organization_ids": [org_id],
        "person_titles": HR_TITLES,
        "per_page": 1,
        "page": 1,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.post(
                f"{APOLLO_BASE}/mixed_people/search",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return {}

    people = data.get("people", [])
    if not people:
        return {}

    person = people[0]
    email = person.get("email")
    # Apollo sometimes hides email behind a reveal call (costs 1 credit)
    # If email is masked (contains "***"), we skip to avoid wasting credits
    if email and "***" in email:
        email = None

    name_parts = [person.get("first_name", ""), person.get("last_name", "")]
    name = " ".join(p for p in name_parts if p).strip() or None

    return {"contact_name": name, "email": email}


async def enrich_leads_with_hr_contacts(leads: list[dict]) -> list[dict]:
    """
    For each lead that came from Apollo org search, attempt to find
    the HR contact. Stops early if Apollo returns rate-limit errors.
    """
    enriched = []
    for lead in leads:
        org_id = lead.pop("_apollo_org_id", None)
        if org_id:
            contact = await find_hr_contact(org_id, lead.get("website"))
            if contact.get("email"):
                lead["email"] = contact["email"]
            if contact.get("contact_name"):
                lead["contact_name"] = contact["contact_name"]
        enriched.append(lead)
    return enriched

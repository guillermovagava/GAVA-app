"""
Hunter.io API integration.
Given a company domain, Hunter.io returns all known email addresses
associated with it, including names and job titles.

Free tier : 25 searches/month  → great for starting out
Starter   : $49/month for 500  → enough for active outreach

Docs: https://hunter.io/api-documentation
"""
import os
import httpx
from typing import Optional
from services.hunter_quota import can_use, increment

HUNTER_BASE = "https://api.hunter.io/v2"

HR_KEYWORDS = ["hr", "human", "recruit", "talent", "hiring", "career", "people", "workforce"]


async def find_hr_contact(domain: str) -> dict:
    """
    Search Hunter.io for the best HR/recruitment contact at a given domain.
    Returns {"email": ..., "contact_name": ..., "position": ...} or {}.

    Falls back to the first available email if no HR-specific one is found.
    Consumes 1 Hunter.io search credit per call.
    Stops automatically when monthly free quota (25) is reached.
    """
    api_key = os.getenv("HUNTER_API_KEY", "")
    if not api_key or not domain:
        return {}

    # Stop if monthly free quota is used up — fall back to web scraper
    if not can_use():
        return {}

    # Strip protocol and path — Hunter.io wants just the domain
    domain = _clean_domain(domain)
    if not domain:
        return {}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{HUNTER_BASE}/domain-search",
                params={"domain": domain, "api_key": api_key, "limit": 10},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return {}

    emails = data.get("data", {}).get("emails", [])
    if not emails:
        return {}

    # Count this as a used credit
    increment()

    # Score each email: higher = more likely to be HR/recruitment
    def score(entry: dict) -> int:
        parts = [
            (entry.get("value") or "").lower(),
            (entry.get("position") or "").lower(),
            (entry.get("department") or "").lower(),
        ]
        combined = " ".join(parts)
        for i, kw in enumerate(HR_KEYWORDS):
            if kw in combined:
                return len(HR_KEYWORDS) - i
        return 0

    emails.sort(key=score, reverse=True)
    best = emails[0]

    first = best.get("first_name", "") or ""
    last  = best.get("last_name", "")  or ""
    name  = f"{first} {last}".strip() or None

    return {
        "email":        best.get("value"),
        "contact_name": name,
        "position":     best.get("position"),
    }


async def verify_email(email: str) -> bool:
    """
    Optional: verify that an email address actually exists before sending.
    Consumes 1 Hunter.io verification credit.
    """
    api_key = os.getenv("HUNTER_API_KEY", "")
    if not api_key:
        return True  # assume valid if we can't check

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"{HUNTER_BASE}/email-verifier",
                params={"email": email, "api_key": api_key},
            )
            resp.raise_for_status()
            status = resp.json().get("data", {}).get("status")
            return status in ("valid", "accept_all")
        except Exception:
            return True


def _clean_domain(url: str) -> Optional[str]:
    """Extract bare domain from a URL string."""
    if not url:
        return None
    url = url.lower().strip()
    for prefix in ("https://", "http://", "www."):
        if url.startswith(prefix):
            url = url[len(prefix):]
    # Remove path
    url = url.split("/")[0].split("?")[0]
    # Must have at least one dot and no spaces
    if "." not in url or " " in url:
        return None
    return url

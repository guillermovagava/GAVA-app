"""
Crawls a business website to find HR / recruitment email addresses.
Priority order: hr@, careers@, recruiting@, hiring@, jobs@, then any contact email.
"""
import re
import httpx
from bs4 import BeautifulSoup
from typing import Optional

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

HR_KEYWORDS = ["hr", "career", "recruit", "hiring", "job", "talent", "people", "human"]
CONTACT_PATHS = ["/contact", "/about", "/careers", "/jobs", "/hr", "/contact-us", "/about-us"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _score_email(email: str) -> int:
    """Higher score = more likely to be an HR/recruitment address."""
    local = email.split("@")[0].lower()
    for i, kw in enumerate(HR_KEYWORDS):
        if kw in local:
            return len(HR_KEYWORDS) - i
    return 0


def _extract_emails(html: str) -> list[str]:
    emails = EMAIL_RE.findall(html)
    # Filter out common non-human addresses
    filtered = [
        e for e in emails
        if not any(skip in e.lower() for skip in ["example.", "sentry.", "wix.", "wordpress.", ".png", ".jpg"])
    ]
    return list(dict.fromkeys(filtered))  # deduplicate while preserving order


async def find_hr_email(website_url: str) -> Optional[str]:
    """Attempt to find an HR/recruitment email from a business website."""
    if not website_url:
        return None

    base = website_url.rstrip("/").split("?")[0]
    # Strip Yelp redirect wrapper if present
    if "yelp.com/biz_redir" in base:
        return None

    all_emails: list[str] = []

    async with httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        headers=HEADERS,
    ) as client:
        # Try homepage first
        try:
            resp = await client.get(base)
            if resp.status_code == 200:
                all_emails.extend(_extract_emails(resp.text))
        except Exception:
            pass

        # Try common contact/careers paths
        for path in CONTACT_PATHS:
            if len(all_emails) >= 10:
                break
            try:
                resp = await client.get(base + path)
                if resp.status_code == 200:
                    all_emails.extend(_extract_emails(resp.text))
            except Exception:
                continue

    if not all_emails:
        return None

    # De-duplicate and rank
    seen = set()
    unique: list[str] = []
    for e in all_emails:
        if e.lower() not in seen:
            seen.add(e.lower())
            unique.append(e)

    unique.sort(key=_score_email, reverse=True)
    return unique[0]


async def extract_contact_name(website_url: str) -> Optional[str]:
    """Best-effort attempt to find a contact person name from About/Team pages."""
    if not website_url:
        return None
    base = website_url.rstrip("/")
    name_patterns = [
        re.compile(r"(?:HR Manager|Human Resources|Recruitment Manager|Hiring Manager)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)"),
        re.compile(r"(?:Director of HR|Head of HR|HR Director)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)"),
    ]

    async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=HEADERS) as client:
        for path in ["/about", "/team", "/about-us", "/our-team"]:
            try:
                resp = await client.get(base + path)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    text = soup.get_text(" ")
                    for pat in name_patterns:
                        m = pat.search(text)
                        if m:
                            return m.group(1)
            except Exception:
                continue
    return None

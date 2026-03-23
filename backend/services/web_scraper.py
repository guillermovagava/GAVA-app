"""
Crawls a business website to find HR / recruitment email addresses.
Priority order: hr@, careers@, recruiting@, hiring@, jobs@, then any contact email.
Optimized for speed: 5s timeout, stops as soon as any email is found, 3 paths max.
"""
import re
import asyncio
import httpx
from typing import Optional

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

HR_KEYWORDS   = ["hr", "career", "recruit", "hiring", "job", "talent", "people", "human"]
CONTACT_PATHS = ["/contact", "/careers", "/about"]   # reduced to 3 — stops early anyway

SKIP_WORDS = ["example.", "sentry.", "wix.", "wordpress.", ".png", ".jpg", "noreply", "no-reply"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _score_email(email: str) -> int:
    local = email.split("@")[0].lower()
    for i, kw in enumerate(HR_KEYWORDS):
        if kw in local:
            return len(HR_KEYWORDS) - i
    return 0


def _extract_emails(html: str) -> list[str]:
    emails = EMAIL_RE.findall(html)
    return [e for e in emails if not any(s in e.lower() for s in SKIP_WORDS)]


async def find_hr_email(website_url: str) -> Optional[str]:
    """
    Attempt to find an HR/recruitment email from a business website.
    Stops as soon as a good email is found — much faster than scanning all pages.
    Timeout: 5s per request (was 10s).
    """
    if not website_url:
        return None

    base = website_url.rstrip("/").split("?")[0]
    if "yelp.com/biz_redir" in base:
        return None

    async with httpx.AsyncClient(
        timeout=5,                # was 10s — faster failure on slow sites
        follow_redirects=True,
        headers=HEADERS,
    ) as client:
        # Try homepage first
        try:
            resp = await client.get(base)
            if resp.status_code == 200:
                emails = _extract_emails(resp.text)
                best = _best_email(emails)
                if best:
                    return best      # ← stop immediately if homepage has an email
        except Exception:
            pass

        # Try contact/careers/about — stop as soon as we find anything
        for path in CONTACT_PATHS:
            try:
                resp = await client.get(base + path)
                if resp.status_code == 200:
                    emails = _extract_emails(resp.text)
                    best = _best_email(emails)
                    if best:
                        return best  # ← stop as soon as first email found
            except Exception:
                continue

    return None


def _best_email(emails: list[str]) -> Optional[str]:
    if not emails:
        return None
    seen, unique = set(), []
    for e in emails:
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
    async with httpx.AsyncClient(timeout=5, follow_redirects=True, headers=HEADERS) as client:
        for path in ["/about", "/team"]:
            try:
                resp = await client.get(base + path)
                if resp.status_code == 200:
                    for pat in name_patterns:
                        m = pat.search(resp.text)
                        if m:
                            return m.group(1)
            except Exception:
                continue
    return None

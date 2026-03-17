"""
Scraper router — runs searches via Yelp, Google Places, or Apollo
in the background and saves leads to the DB.
"""
import asyncio
import os
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import Lead, ScrapeJob
from services.yelp_service import search_businesses as yelp_search, SEASONAL_CATEGORIES
from services.google_places_service import search_businesses as google_search, GOOGLE_CATEGORIES
from services.apollo_service import search_companies as apollo_search, enrich_leads_with_hr_contacts, APOLLO_INDUSTRIES

router = APIRouter()

US_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY",
]
CA_PROVINCES = ["BC","AB","ON","QC","NS","NB","MB","SK","PE","NL"]

STATE_CITIES: dict[str, list[str]] = {
    "FL": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale"],
    "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento", "Anaheim"],
    "NY": ["New York City", "Buffalo", "Albany", "Rochester", "Syracuse"],
    "TX": ["Houston", "Dallas", "Austin", "San Antonio", "El Paso"],
    "CO": ["Denver", "Colorado Springs", "Aspen", "Vail", "Breckenridge"],
    "HI": ["Honolulu", "Maui", "Kauai", "Kailua-Kona"],
    "NV": ["Las Vegas", "Reno", "Lake Tahoe"],
    "AZ": ["Phoenix", "Scottsdale", "Sedona", "Tucson"],
}


class QuickScrapeRequest(BaseModel):
    category_label: str
    states: list[str]
    source: str = "yelp"   # "yelp" | "google" | "apollo"


@router.get("/categories")
def get_categories():
    """Return available categories per source so the UI can show the right options."""
    return {
        "yelp":   SEASONAL_CATEGORIES,
        "google": GOOGLE_CATEGORIES,
        "apollo": [{"label": i.title(), "query": i} for i in APOLLO_INDUSTRIES],
    }


@router.get("/sources")
def get_sources():
    """Which sources are currently configured (have API keys in .env)."""
    return {
        "yelp":   bool(os.getenv("YELP_API_KEY")),
        "google": bool(os.getenv("GOOGLE_PLACES_API_KEY")),
        "apollo": bool(os.getenv("APOLLO_API_KEY")),
    }


@router.post("/quick")
async def quick_scrape(
    payload: QuickScrapeRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    locations: list[str] = []
    for state in payload.states:
        cities = STATE_CITIES.get(state, [])
        if cities:
            locations.extend([f"{city}, {state}" for city in cities])
        else:
            locations.append(state)

    job = ScrapeJob(
        category=f"[{payload.source.upper()}] {payload.category_label}",
        location=", ".join(payload.states),
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background.add_task(
        _scrape_task,
        job.id,
        payload.source,
        payload.category_label,
        locations,
    )
    return {"job_id": job.id, "status": "started", "locations_queued": len(locations)}


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(ScrapeJob).order_by(ScrapeJob.created_at.desc()).limit(50).all()
    return [_serialize_job(j) for j in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
    if not job:
        return {"error": "Job not found"}
    return _serialize_job(job)


# ── Background task ──────────────────────────────────────────────────────────

LEAD_COLUMNS = {c.name for c in Lead.__table__.columns}


async def _scrape_task(job_id: int, source: str, category_label: str, locations: list[str]):
    db = SessionLocal()
    try:
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        total_saved = 0

        # ── Yelp ─────────────────────────────────────────────────────────────
        if source == "yelp":
            from services.yelp_service import SEASONAL_CATEGORIES as YELP_CATS
            cat = next((c for c in YELP_CATS if c["label"] == category_label), None)
            yelp_key = cat["yelp"] if cat else category_label.lower()
            for location in locations:
                try:
                    results = await yelp_search(yelp_key, location, limit=50)
                except Exception:
                    continue
                for biz in results:
                    yelp_id = biz.get("yelp_id")
                    if yelp_id and db.query(Lead).filter(Lead.yelp_id == yelp_id).first():
                        continue
                    lead = Lead(**{k: v for k, v in biz.items() if k in LEAD_COLUMNS})
                    db.add(lead)
                    total_saved += 1
                db.commit()
                await asyncio.sleep(0.5)

        # ── Google Places ─────────────────────────────────────────────────────
        elif source == "google":
            from services.google_places_service import GOOGLE_CATEGORIES as G_CATS
            cat = next((c for c in G_CATS if c["label"] == category_label), None)
            query = cat["query"] if cat else category_label
            for location in locations:
                try:
                    results = await google_search(query, location, max_results=20)
                except Exception:
                    continue
                for biz in results:
                    # Dedup by business name + city (Google has no stable ID in free tier)
                    exists = db.query(Lead).filter(
                        Lead.business_name == biz.get("business_name"),
                        Lead.city == biz.get("city"),
                    ).first()
                    if exists:
                        continue
                    lead = Lead(**{k: v for k, v in biz.items() if k in LEAD_COLUMNS})
                    db.add(lead)
                    total_saved += 1
                db.commit()
                await asyncio.sleep(2)  # Google Places requires delay between pages

        # ── Apollo.io ─────────────────────────────────────────────────────────
        elif source == "apollo":
            industry = category_label.lower()
            for location in locations:
                try:
                    results = await apollo_search(industry, location, per_page=25)
                    results = await enrich_leads_with_hr_contacts(results)
                except Exception:
                    continue
                for biz in results:
                    exists = db.query(Lead).filter(
                        Lead.business_name == biz.get("business_name"),
                        Lead.city == biz.get("city"),
                    ).first()
                    if exists:
                        continue
                    lead = Lead(**{k: v for k, v in biz.items() if k in LEAD_COLUMNS})
                    db.add(lead)
                    total_saved += 1
                db.commit()
                await asyncio.sleep(1)

        job.status = "done"
        job.leads_found = total_saved
        job.finished_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def _serialize_job(job: ScrapeJob) -> dict:
    return {
        "id": job.id,
        "category": job.category,
        "location": job.location,
        "status": job.status,
        "leads_found": job.leads_found,
        "error": job.error,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }

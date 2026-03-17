"""
Scraper router — runs Yelp searches in the background and saves leads to the DB.
"""
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import Lead, ScrapeJob
from services.yelp_service import search_businesses, SEASONAL_CATEGORIES

router = APIRouter()

# US states + Canadian provinces commonly targeted for seasonal staffing
US_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY",
]
CA_PROVINCES = ["BC","AB","ON","QC","NS","NB","MB","SK","PE","NL"]

# Major cities per state (used to improve Yelp coverage — Yelp caps at 1000/search area)
STATE_CITIES: dict[str, list[str]] = {
    "FL": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale"],
    "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento", "Anaheim"],
    "NY": ["New York City", "Buffalo", "Albany", "Rochester", "Syracuse"],
    "TX": ["Houston", "Dallas", "Austin", "San Antonio", "El Paso"],
    "CO": ["Denver", "Colorado Springs", "Aspen", "Vail", "Breckenridge"],
    "HI": ["Honolulu", "Maui", "Kauai", "Kailua-Kona"],
    "NV": ["Las Vegas", "Reno", "Lake Tahoe"],
    "AZ": ["Phoenix", "Scottsdale", "Sedona", "Tucson"],
    # Default for states not listed: use the state abbreviation directly
}


class ScrapeRequest(BaseModel):
    category: str           # yelp category key e.g. "hotels"
    locations: list[str]    # list of "City, ST" strings
    max_per_location: int = 50


class QuickScrapeRequest(BaseModel):
    category_label: str     # human-friendly label from SEASONAL_CATEGORIES
    states: list[str]       # list of state/province abbreviations


@router.get("/categories")
def get_categories():
    return SEASONAL_CATEGORIES


@router.post("/run")
async def run_scrape(payload: ScrapeRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    """Start a scrape job for a specific category + list of locations."""
    job = ScrapeJob(
        category=payload.category,
        location=", ".join(payload.locations),
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background.add_task(_scrape_task, job.id, payload.category, payload.locations, payload.max_per_location)
    return {"job_id": job.id, "status": "started"}


@router.post("/quick")
async def quick_scrape(payload: QuickScrapeRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    """Convenience endpoint: pick a category label + states, we build the location list."""
    cat = next((c for c in SEASONAL_CATEGORIES if c["label"] == payload.category_label), None)
    if not cat:
        return {"error": f"Unknown category: {payload.category_label}"}

    locations: list[str] = []
    for state in payload.states:
        cities = STATE_CITIES.get(state, [])
        if cities:
            locations.extend([f"{city}, {state}" for city in cities])
        else:
            locations.append(state)

    job = ScrapeJob(
        category=cat["yelp"],
        location=", ".join(payload.states),
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background.add_task(_scrape_task, job.id, cat["yelp"], locations, 50)
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

async def _scrape_task(job_id: int, category: str, locations: list[str], max_per: int):
    db = SessionLocal()
    try:
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        total_saved = 0
        for location in locations:
            try:
                results = await search_businesses(category, location, limit=max_per)
            except Exception:
                continue

            for biz in results:
                yelp_id = biz.get("yelp_id")
                # Deduplication by yelp_id
                if yelp_id and db.query(Lead).filter(Lead.yelp_id == yelp_id).first():
                    continue
                lead = Lead(**{k: v for k, v in biz.items() if k in Lead.__table__.columns.keys()})
                db.add(lead)
                total_saved += 1

            db.commit()
            await asyncio.sleep(0.5)  # be kind to the API

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

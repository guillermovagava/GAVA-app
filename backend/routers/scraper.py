"""
Scraper router — uses Google Places to find businesses and
Hunter.io (or free web scraper as fallback) to find HR emails.
"""
import asyncio
import os
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import Lead, ScrapeJob
from services.google_places_service import search_businesses, GOOGLE_CATEGORIES

router = APIRouter()

STATE_CITIES: dict[str, list[str]] = {
    "FL": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale"],
    "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento", "Anaheim"],
    "NY": ["New York City", "Buffalo", "Albany", "Rochester", "Syracuse"],
    "TX": ["Houston", "Dallas", "Austin", "San Antonio", "El Paso"],
    "CO": ["Denver", "Colorado Springs", "Aspen", "Vail", "Breckenridge"],
    "HI": ["Honolulu", "Maui", "Kauai", "Kailua-Kona"],
    "NV": ["Las Vegas", "Reno", "Lake Tahoe"],
    "AZ": ["Phoenix", "Scottsdale", "Sedona", "Tucson"],
    "WA": ["Seattle", "Spokane", "Bellevue", "Tacoma"],
    "OR": ["Portland", "Eugene", "Bend", "Salem"],
    "GA": ["Atlanta", "Savannah", "Augusta", "Macon"],
    "NC": ["Charlotte", "Raleigh", "Asheville", "Wilmington"],
    "SC": ["Charleston", "Myrtle Beach", "Hilton Head", "Columbia"],
    "VA": ["Virginia Beach", "Richmond", "Charlottesville", "Roanoke"],
    "MI": ["Detroit", "Traverse City", "Grand Rapids", "Ann Arbor"],
    "MN": ["Minneapolis", "Duluth", "Rochester", "Brainerd"],
    "WI": ["Milwaukee", "Madison", "Green Bay", "Wisconsin Dells"],
    "IL": ["Chicago", "Springfield", "Galena", "Rockford"],
    "PA": ["Philadelphia", "Pittsburgh", "Hershey", "Lancaster"],
    "MA": ["Boston", "Cape Cod", "Springfield", "Worcester"],
    "ME": ["Portland", "Bar Harbor", "Kennebunkport", "Bangor"],
    "NH": ["Manchester", "Portsmouth", "Conway", "Laconia"],
    "VT": ["Burlington", "Stowe", "Montpelier", "Brattleboro"],
    # Canada
    "BC": ["Vancouver", "Victoria", "Whistler", "Kelowna"],
    "AB": ["Calgary", "Edmonton", "Banff", "Jasper"],
    "ON": ["Toronto", "Ottawa", "Niagara Falls", "Muskoka"],
    "QC": ["Montreal", "Quebec City", "Mont-Tremblant"],
    # Australia
    "NSW": ["Sydney", "Newcastle", "Wollongong", "Byron Bay", "Port Macquarie"],
    "VIC": ["Melbourne", "Geelong", "Ballarat", "Bendigo", "Mornington"],
    "QLD": ["Brisbane", "Gold Coast", "Cairns", "Townsville", "Noosa", "Whitsundays"],
    "WA":  ["Perth", "Fremantle", "Broome", "Margaret River", "Exmouth"],
    "SA":  ["Adelaide", "Port Augusta", "Kangaroo Island", "Barossa Valley"],
    "TAS": ["Hobart", "Launceston", "Cradle Mountain", "Freycinet"],
    "NT":  ["Darwin", "Alice Springs", "Kakadu"],
    "ACT": ["Canberra"],
}


class ScrapeRequest(BaseModel):
    category_label: str
    states: list[str] = []
    custom_locations: list[str] = []   # e.g. ["Miami Beach, FL", "Aspen, CO"]
    hunter_credits: int = 5   # max Hunter.io credits to spend on this job (0 = none)
    max_results_per_city: int = 20


@router.get("/categories")
def get_categories():
    return GOOGLE_CATEGORIES


@router.get("/status")
def get_status():
    """Shows which API keys are configured."""
    return {
        "google_places": bool(os.getenv("GOOGLE_PLACES_API_KEY")),
        "hunter":        bool(os.getenv("HUNTER_API_KEY")),
        "email_fallback": True,   # web scraper is always available
    }


@router.post("/run")
async def run_scrape(
    payload: ScrapeRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    cat = next((c for c in GOOGLE_CATEGORIES if c["label"] == payload.category_label), None)
    if not cat:
        return {"error": f"Unknown category: {payload.category_label}"}

    # Build city-level location list
    locations: list[str] = []
    for state in payload.states:
        cities = STATE_CITIES.get(state, [])
        if cities:
            locations.extend([f"{city}, {state}" for city in cities])
        else:
            locations.append(state)
    # Add custom locations directly
    for loc in payload.custom_locations:
        if loc.strip() and loc.strip() not in locations:
            locations.append(loc.strip())

    job = ScrapeJob(
        category=payload.category_label,
        location=", ".join(payload.states),
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background.add_task(_scrape_task, job.id, cat["query"], locations, payload.hunter_credits, payload.max_results_per_city)
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


async def _scrape_task(job_id: int, query: str, locations: list[str], hunter_credits: int = 5, payload_max_results: int = 20):
    db = SessionLocal()
    try:
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        total_saved = 0
        # Mutable counter shared across all location searches in this job
        hunter_used = [0]

        for location in locations:
            try:
                results = await search_businesses(
                    query, location,
                    max_results=payload_max_results,
                    hunter_budget=hunter_credits,
                    hunter_used=hunter_used,
                )
            except Exception:
                continue

            for biz in results:
                # Deduplicate by name + city
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
            await asyncio.sleep(2)  # respect API rate limits

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
        "id":          job.id,
        "category":    job.category,
        "location":    job.location,
        "status":      job.status,
        "leads_found": job.leads_found,
        "error":       job.error,
        "started_at":  job.started_at.isoformat()  if job.started_at  else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at":  job.created_at.isoformat()  if job.created_at  else None,
    }

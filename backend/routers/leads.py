from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from database import get_db
from models import Lead, EmailLog

router = APIRouter()


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    business_name: str
    category: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "US"
    lat: Optional[float] = None
    lng: Optional[float] = None
    contact_name: Optional[str] = None
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    business_name: Optional[str] = None
    category: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    contact_name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/")
def list_leads(
    db: Session = Depends(get_db),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 500,
):
    q = db.query(Lead)
    if state:
        q = q.filter(Lead.state == state)
    if category:
        q = q.filter(Lead.category.ilike(f"%{category}%"))
    if status:
        q = q.filter(Lead.status == status)
    if search:
        q = q.filter(
            Lead.business_name.ilike(f"%{search}%") |
            Lead.city.ilike(f"%{search}%") |
            Lead.email.ilike(f"%{search}%")
        )
    total = q.count()
    leads = q.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "leads": [_serialize(l) for l in leads]}


@router.get("/map-pins")
def map_pins(db: Session = Depends(get_db)):
    """Lightweight endpoint — returns only fields needed to render map pins."""
    leads = db.query(
        Lead.id, Lead.business_name, Lead.city, Lead.state,
        Lead.lat, Lead.lng, Lead.status, Lead.category
    ).filter(Lead.lat.isnot(None), Lead.lng.isnot(None)).all()
    return [
        {
            "id": l.id, "business_name": l.business_name,
            "city": l.city, "state": l.state,
            "lat": l.lat, "lng": l.lng,
            "status": l.status, "category": l.category,
        }
        for l in leads
    ]


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Lead.id)).scalar()
    by_status = db.query(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()
    by_state = db.query(Lead.state, func.count(Lead.id)).group_by(Lead.state).order_by(func.count(Lead.id).desc()).limit(10).all()
    return {
        "total": total,
        "by_status": {s: c for s, c in by_status},
        "top_states": [{"state": s, "count": c} for s, c in by_state],
    }


@router.get("/filters")
def filter_options(db: Session = Depends(get_db)):
    states = db.query(Lead.state).distinct().filter(Lead.state.isnot(None)).all()
    categories = db.query(Lead.category).distinct().filter(Lead.category.isnot(None)).all()
    return {
        "states": sorted([s[0] for s in states if s[0]]),
        "categories": sorted(list(set(
            cat.strip()
            for row in categories if row[0]
            for cat in row[0].split(",")
            if cat.strip()
        ))),
    }


@router.get("/{lead_id}")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    data = _serialize(lead)
    data["email_history"] = [
        {"id": e.id, "subject": e.subject, "body": e.body, "sent_at": e.sent_at.isoformat()}
        for e in lead.emails
    ]
    return data


@router.post("/")
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _serialize(lead)


@router.patch("/{lead_id}")
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return _serialize(lead)


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"deleted": True}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _serialize(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "business_name": lead.business_name,
        "category": lead.category,
        "email": lead.email,
        "phone": lead.phone,
        "website": lead.website,
        "address": lead.address,
        "city": lead.city,
        "state": lead.state,
        "country": lead.country,
        "lat": lead.lat,
        "lng": lead.lng,
        "contact_name": lead.contact_name,
        "status": lead.status,
        "source": lead.source,
        "notes": lead.notes,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "last_contacted": lead.last_contacted.isoformat() if lead.last_contacted else None,
    }

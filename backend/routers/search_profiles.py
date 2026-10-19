"""
AI Search Profiles — let users describe target businesses in natural language.
Claude converts the description into a Google Places search query and saves it for reuse.
"""
import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import SearchProfile

router = APIRouter()


class CreateProfileRequest(BaseModel):
    name: str
    description: str


def _generate_query(description: str) -> str:
    """Ask Claude to convert a natural language description into a Places search query."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return description[:60]

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=60,
            messages=[{
                "role": "user",
                "content": (
                    "Convert this business description into a short Google Places search query "
                    "(2-5 words, English only, no location, no quotes).\n\n"
                    f"Description: {description}\n\n"
                    "Reply with ONLY the search query, nothing else."
                ),
            }],
        )
        return msg.content[0].text.strip().strip('"').strip("'")
    except Exception:
        return description[:60]


def _serialize(p: SearchProfile) -> dict:
    return {
        "id":          p.id,
        "name":        p.name,
        "description": p.description,
        "query":       p.query,
        "created_at":  p.created_at.isoformat() if p.created_at else None,
    }


@router.get("/")
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.query(SearchProfile).order_by(SearchProfile.created_at.desc()).all()
    return [_serialize(p) for p in profiles]


@router.post("/")
def create_profile(payload: CreateProfileRequest, db: Session = Depends(get_db)):
    query = _generate_query(payload.description)
    profile = SearchProfile(
        name=payload.name,
        description=payload.description,
        query=query,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _serialize(profile)


@router.delete("/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(SearchProfile).filter(SearchProfile.id == profile_id).first()
    if not profile:
        return {"error": "Not found"}
    db.delete(profile)
    db.commit()
    return {"deleted": True}

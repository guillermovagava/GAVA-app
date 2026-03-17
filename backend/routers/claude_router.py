from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from services.claude_service import draft_email

router = APIRouter()


class DraftRequest(BaseModel):
    business_name: str
    contact_name: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    tone: Optional[str] = "professional"
    custom_instructions: Optional[str] = ""


@router.post("/draft-email")
def draft(payload: DraftRequest):
    result = draft_email(
        business_name=payload.business_name,
        contact_name=payload.contact_name,
        category=payload.category,
        city=payload.city,
        state=payload.state,
        tone=payload.tone or "professional",
        custom_instructions=payload.custom_instructions or "",
    )
    if "error" in result:
        return {"error": result["error"]}
    return result

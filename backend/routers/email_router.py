from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Lead, EmailLog
from services.email_service import send_email

router = APIRouter()


class SendEmailRequest(BaseModel):
    lead_id: int
    subject: str
    body: str


@router.post("/send")
def send(payload: SendEmailRequest, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.email:
        raise HTTPException(status_code=400, detail="Lead has no email address")

    result = send_email(lead.email, payload.subject, payload.body)

    if result["success"]:
        # Log the email
        log = EmailLog(lead_id=lead.id, subject=payload.subject, body=payload.body)
        db.add(log)
        # Update lead status and last_contacted
        if lead.status == "new":
            lead.status = "contacted"
        lead.last_contacted = datetime.utcnow()
        db.commit()
        return {"success": True, "message": f"Email sent to {lead.email}"}
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send email"))

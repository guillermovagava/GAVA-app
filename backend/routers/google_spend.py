"""Google Places spend: summary (real + internal), manual billing sync."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services import google_billing, google_spend

router = APIRouter()


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Real net spend of the month (Cloud Billing), internal estimate (call counter), free calls left per SKU,
    month-end projection and last sync time."""
    return google_spend.summary(db)


@router.post("/sync")
def sync_now(db: Session = Depends(get_db)):
    """Manual 'refresh' of the billing data (same job that runs daily)."""
    result = google_billing.sync(db)
    return {**result, "summary": google_spend.summary(db)}

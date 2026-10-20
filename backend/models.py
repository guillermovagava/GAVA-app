from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, Date, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class SearchProfile(Base):
    __tablename__ = "search_profiles"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    description = Column(Text, nullable=False)   # user's natural language description
    query       = Column(String, nullable=False)  # Claude-generated Places API query
    created_at  = Column(DateTime, default=datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, nullable=False)
    category = Column(String)
    email = Column(String)
    phone = Column(String)
    website = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    country = Column(String, default="US")
    lat = Column(Float)
    lng = Column(Float)
    contact_name = Column(String)
    position = Column(String, nullable=True)
    # new | contacted | replied | meeting_booked | converted
    status = Column(String, default="new")
    source = Column(String)          # google | manual
    email_source = Column(String)    # hunter | scraper | None
    photo_ref = Column(String)       # Google Places photo resource name
    notes = Column(Text)
    yelp_id = Column(String, unique=True, nullable=True)
    archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_contacted = Column(DateTime, nullable=True)

    emails = relationship("EmailLog", back_populates="lead", cascade="all, delete-orphan")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"))
    subject = Column(String)
    body = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="emails")


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String)
    location = Column(String)
    status = Column(String, default="pending")  # pending | running | done | failed
    leads_found = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GoogleApiUsage(Base):
    """One row per batch of billable Google Places calls (persisted counter; survives deploys)."""
    __tablename__ = "google_api_usage"

    id         = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    month_key  = Column(String(7), nullable=False, index=True)   # 'YYYY-MM' (UTC)
    sku        = Column(String, nullable=False)
    calls      = Column(Integer, nullable=False, default=1)


class GoogleSpendDaily(Base):
    """Real spend per day and SKU, synced from the Cloud Billing export in BigQuery."""
    __tablename__ = "google_spend_daily"
    __table_args__ = (UniqueConstraint("date", "sku", name="uq_google_spend_daily_date_sku"),)

    id          = Column(Integer, primary_key=True, index=True)
    date        = Column(Date, nullable=False, index=True)
    sku         = Column(String, nullable=False)
    cost_usd    = Column(Float, nullable=False, default=0.0)
    credits_usd = Column(Float, nullable=False, default=0.0)   # negative numbers (credits reduce the bill)
    net_usd     = Column(Float, nullable=False, default=0.0)
    synced_at   = Column(DateTime, default=datetime.utcnow, nullable=False)


class GoogleBillingSync(Base):
    """Log of billing syncs, so the UI can tell 'never synced' / 'no data yet' / 'error' apart from $0."""
    __tablename__ = "google_billing_sync"

    id        = Column(Integer, primary_key=True, index=True)
    synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status    = Column(String, nullable=False)    # ok | no_data | not_configured | error
    message   = Column(Text, nullable=True)
    rows      = Column(Integer, default=0)

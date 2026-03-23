from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


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
    # new | contacted | replied | meeting_booked | converted
    status = Column(String, default="new")
    source = Column(String)          # google | manual
    email_source = Column(String)    # hunter | scraper | None
    notes = Column(Text)
    yelp_id = Column(String, unique=True, nullable=True)
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

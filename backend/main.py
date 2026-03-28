from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one folder above /backend)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models  # noqa: F401 — registers all models before create_all

from routers import leads, scraper, email_router, claude_router

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# ── Startup migrations (safe, idempotent) ─────────────────────────────────────
from sqlalchemy import text as _text
with engine.connect() as _conn:
    _cols = [r[1] for r in _conn.execute(_text("PRAGMA table_info(leads)")).fetchall()]
    if "archived" not in _cols:
        _conn.execute(_text("ALTER TABLE leads ADD COLUMN archived INTEGER DEFAULT 0 NOT NULL"))
        _conn.commit()
    if "position" not in _cols:
        _conn.execute(_text("ALTER TABLE leads ADD COLUMN position TEXT"))
        _conn.commit()

app = FastAPI(title="GAVA Recruitment CRM", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])
app.include_router(email_router.router, prefix="/api/email", tags=["email"])
app.include_router(claude_router.router, prefix="/api/claude", tags=["claude"])


@app.get("/api/health")
def health():
    return {"status": "ok"}

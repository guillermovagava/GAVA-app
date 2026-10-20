import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
# In frozen mode (.exe), look for .env next to the executable.
# In dev mode, look two levels above backend/ (project root).
# On Railway, environment variables are injected directly — no .env file needed.
if getattr(sys, 'frozen', False):
    _env_path = Path(os.path.dirname(sys.executable)) / ".env"
else:
    _env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base
import models  # noqa: F401 — registers all models before create_all

from routers import leads, scraper, email_router, claude_router, search_profiles, google_spend

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# ── Startup migrations (SQLite only — safe, idempotent) ──────────────────────
# PostgreSQL (Railway) gets a fresh schema from create_all above.
if not os.getenv("DATABASE_URL"):
    from sqlalchemy import text as _text
    with engine.connect() as _conn:
        _cols = [r[1] for r in _conn.execute(_text("PRAGMA table_info(leads)")).fetchall()]
        if "archived" not in _cols:
            _conn.execute(_text("ALTER TABLE leads ADD COLUMN archived INTEGER DEFAULT 0 NOT NULL"))
            _conn.commit()
        if "position" not in _cols:
            _conn.execute(_text("ALTER TABLE leads ADD COLUMN position TEXT"))
            _conn.commit()

# ── Google billing: one-time legacy counter import + daily sync ──────────────
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta


async def _billing_sync_loop():
    """Daily Cloud Billing → google_spend_daily sync (no scheduler dependency: plain asyncio task)."""
    from database import SessionLocal
    from services import google_billing
    await asyncio.sleep(30)
    while True:
        try:
            if google_billing.is_configured():
                db = SessionLocal()
                try:
                    last = google_billing.last_sync(db)
                    # skip if a deploy restart happens within a day of the previous sync
                    if last is None or datetime.utcnow() - last.synced_at > timedelta(hours=20):
                        await asyncio.to_thread(google_billing.sync, db)
                finally:
                    db.close()
        except Exception:
            pass
        await asyncio.sleep(24 * 3600)


@asynccontextmanager
async def lifespan(_app):
    try:
        from services import google_quota
        google_quota.import_legacy_file()
    except Exception:
        pass
    task = asyncio.create_task(_billing_sync_loop())
    yield
    task.cancel()


app = FastAPI(title="GAVA Recruitment CRM", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router,           prefix="/api/leads",           tags=["leads"])
app.include_router(scraper.router,         prefix="/api/scraper",         tags=["scraper"])
app.include_router(email_router.router,    prefix="/api/email",           tags=["email"])
app.include_router(claude_router.router,   prefix="/api/claude",          tags=["claude"])
app.include_router(search_profiles.router, prefix="/api/search-profiles", tags=["search-profiles"])
app.include_router(google_spend.router,    prefix="/api/google-spend",    tags=["google-spend"])


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Serve React SPA (built frontend) ─────────────────────────────────────────
# Active when frontend/dist has been built and copied to backend/static/
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_static_dir):
    _assets_dir = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        fp = os.path.join(_static_dir, full_path)
        if os.path.isfile(fp):
            return FileResponse(fp)
        return FileResponse(os.path.join(_static_dir, "index.html"))

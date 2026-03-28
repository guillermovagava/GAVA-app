import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────
# In frozen mode (.exe), look for .env next to the executable.
# In dev mode, look two levels above backend/ (project root).
if getattr(sys, 'frozen', False):
    _env_path = Path(os.path.dirname(sys.executable)) / ".env"
else:
    _env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router,        prefix="/api/leads",  tags=["leads"])
app.include_router(scraper.router,      prefix="/api/scraper", tags=["scraper"])
app.include_router(email_router.router, prefix="/api/email",  tags=["email"])
app.include_router(claude_router.router,prefix="/api/claude", tags=["claude"])


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── Serve React SPA (built frontend) ─────────────────────────────────────────
# Only active when frontend/dist has been built and copied to backend/static/
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_static_dir):
    # Serve /assets and other Vite output folders
    _assets_dir = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        fp = os.path.join(_static_dir, full_path)
        if os.path.isfile(fp):
            return FileResponse(fp)
        # SPA fallback — always return index.html
        return FileResponse(os.path.join(_static_dir, "index.html"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models  # noqa: F401 — registers all models before create_all

from routers import leads, scraper, email_router, claude_router

# Create all tables on startup
Base.metadata.create_all(bind=engine)

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

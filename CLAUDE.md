# GAVA Recruitment CRM — Claude Code Context

## What this project is

A local desktop CRM for hospitality & event industry recruiting. Searches Google Maps for target businesses, enriches leads with HR contacts, drafts outreach emails via Claude AI, and tracks the full pipeline. Runs entirely on-machine (Windows); no cloud hosting.

## Architecture

```
FastAPI backend (port 8000)  ←→  React/Vite frontend (port 5173, dev)
         ↓
     SQLite (backend/gava.db)
```

In production, `build.bat` compiles the React app into `backend/static/` and bundles everything into a single `.exe` via PyInstaller. The FastAPI server then serves the SPA directly.

## Key files

| File | Purpose |
|---|---|
| `backend/main.py` | App entrypoint, router registration, SPA serving, startup migrations |
| `backend/models.py` | Lead, EmailLog, ScrapeJob SQLAlchemy models |
| `backend/routers/scraper.py` | Google Places job queue, STATE_CITIES map |
| `backend/services/google_places_service.py` | Places API calls, GOOGLE_CATEGORIES, quota tracking |
| `backend/services/google_quota.py` | Monthly request counter (file: `backend/google_quota.json`) |
| `backend/services/hunter_quota.py` | Monthly Hunter.io counter (file: `backend/hunter_quota.json`) |
| `frontend/src/components/Scraper/ScraperPanel.jsx` | Main scraper UI — categories, location picker, quota pill, request estimator |

## Dev commands

```bash
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Both at once (Windows)
start.bat
```

## Environment variables

See `.env.example`. Required: `GOOGLE_PLACES_API_KEY`, `ANTHROPIC_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`. Optional: `HUNTER_API_KEY`, `GOOGLE_PLACES_MONTHLY_BUDGET`.

## Data flow for a scrape job

1. User selects categories + states/cities in `ScraperPanel.jsx`
2. `POST /api/scraper/run` creates a `ScrapeJob` row and enqueues a background task
3. `_scrape_task` iterates over locations, calls `search_businesses()` per location
4. `search_businesses()` pages through Places API (≤20 results/page), enriches each place with email via Hunter.io or free web scraper, increments `google_quota`
5. Results deduped by (business_name, city) and saved as `Lead` rows

## Request estimation formula

`estimated_requests = locations × categories × ceil(max_results / 20)`

One `searchText` call per page. Google Places (New) charges per call regardless of result count.

## Adding a new business category

1. Add entry to `GOOGLE_CATEGORIES` in `backend/services/google_places_service.py`
2. No frontend change needed — categories are fetched from `/api/scraper/categories`

## Lead statuses

`new` → `contacted` → `replied` → `meeting_booked` → `converted`  
Any status can also be `archived` (soft delete via `archived=True` flag).

## Database migrations

Done inline in `main.py` at startup using raw `ALTER TABLE` with `PRAGMA table_info` guards. No Alembic — keep it simple.

## Quota JSON files

`backend/google_quota.json` and `backend/hunter_quota.json` are auto-created. They track monthly usage and reset on the 1st. These files are gitignored (they contain runtime state, not config).

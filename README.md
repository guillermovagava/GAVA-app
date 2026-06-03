# GAVA Recruitment CRM

A desktop CRM for hospitality & event recruitment. Searches Google Maps for target businesses, finds HR contacts, drafts personalized outreach emails with Claude AI, and tracks every lead through your pipeline — all from a single local app.

![Tech Stack](https://img.shields.io/badge/Backend-FastAPI%20%2B%20SQLite-009688?style=flat-square) ![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=flat-square) ![AI](https://img.shields.io/badge/AI-Claude%20Sonnet-6C5CE7?style=flat-square)

---

## Features

| Feature | Description |
|---|---|
| **Lead Scraper** | Search Google Maps by business category across US, Canada, and Australia. Finds hotels, resorts, restaurants, golf clubs, event venues, and more. |
| **Contact Enrichment** | Automatically finds HR email addresses via Hunter.io (paid) or free website scanning. |
| **CRM Pipeline** | Kanban-style and table views with statuses: New → Contacted → Replied → Meeting Booked → Converted. |
| **Map View** | Interactive Leaflet map with clustered markers color-coded by lead status. |
| **AI Email Drafting** | Claude Sonnet writes personalized outreach emails based on business name, location, and context. |
| **Email Sending** | Send directly from the app via Gmail App Password — no third-party mail service needed. |
| **API Quota Tracker** | Live display of monthly Google Places API requests used/remaining with per-search estimates. |

---

## Tech Stack

```
frontend/          React 18 + Vite + Leaflet maps + Axios
backend/           FastAPI + SQLAlchemy + SQLite + Uvicorn
AI                 Anthropic Claude Sonnet (email drafting)
APIs               Google Places (New) · Hunter.io · Gmail SMTP
Packaging          PyInstaller (.exe) for Windows distribution
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (LTS)

### 1. Clone & setup

```bash
git clone https://github.com/guillermovagava/GAVA-app.git
cd GAVA-app
setup.bat          # installs Python deps, npm deps, and creates .env from template
```

### 2. Fill in API keys

Open `.env` and add your keys (see [API Keys](#api-keys) section below):

```env
GOOGLE_PLACES_API_KEY=...
ANTHROPIC_API_KEY=...
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...
HUNTER_API_KEY=...   # optional
```

### 3. Run

```bash
start.bat
```

Opens the app automatically at `http://localhost:5173`.

---

## API Keys

| Key | Required | Cost | How to get |
|---|---|---|---|
| `GOOGLE_PLACES_API_KEY` | Yes | Free ($200/month credit, ~6,000 searches) | [Google Cloud Console](https://console.cloud.google.com) → Enable Places API → Credentials → API Key |
| `ANTHROPIC_API_KEY` | Yes | ~$0.01–0.03/email | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `GMAIL_ADDRESS` | Yes | Free | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Yes | Free | Google Account → Security → 2FA ON → App Passwords |
| `HUNTER_API_KEY` | No | Free tier: 25/month | [hunter.io](https://hunter.io) → API |

**Optional env vars:**

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_PLACES_MONTHLY_BUDGET` | `6000` | Override the monthly Places API request budget shown in the UI |

---

## Project Structure

```
GAVA-app/
├── backend/
│   ├── main.py                  # FastAPI app, routes, SPA serving
│   ├── models.py                # SQLAlchemy models (Lead, EmailLog, ScrapeJob)
│   ├── database.py              # SQLite engine + session
│   ├── requirements.txt
│   ├── routers/
│   │   ├── leads.py             # CRUD for leads + pipeline actions
│   │   ├── scraper.py           # Google Places search jobs
│   │   ├── email_router.py      # Email drafting + sending
│   │   └── claude_router.py     # Claude AI endpoints
│   └── services/
│       ├── google_places_service.py  # Places API search + enrichment
│       ├── google_quota.py           # Monthly API request tracker
│       ├── hunter_service.py         # Hunter.io contact finder
│       ├── hunter_quota.py           # Monthly Hunter credit tracker
│       ├── web_scraper.py            # Free email scraper (fallback)
│       ├── claude_service.py         # Anthropic SDK wrapper
│       └── email_service.py          # Gmail SMTP sender
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Scraper/         # Lead scraper UI + quota display
│       │   ├── LeadList/        # Table view + filters
│       │   ├── LeadDetail/      # Lead card + email composer
│       │   ├── Map/             # Leaflet map view
│       │   └── Pipeline/        # Kanban pipeline view
│       └── api/client.js        # Axios API client
├── .env.example                 # Environment variable template
├── setup.bat                    # First-time setup script
├── start.bat                    # Dev server launcher
└── build.bat                    # Build .exe for distribution
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/leads` | List leads (filterable) |
| `POST` | `/api/leads` | Create lead manually |
| `PATCH` | `/api/leads/{id}` | Update lead |
| `DELETE` | `/api/leads/{id}` | Delete lead |
| `GET` | `/api/scraper/categories` | Available business categories |
| `POST` | `/api/scraper/run` | Start a scrape job |
| `GET` | `/api/scraper/jobs` | List all scrape jobs |
| `POST` | `/api/scraper/jobs/{id}/cancel` | Cancel running job |
| `GET` | `/api/scraper/status` | API key status |
| `GET` | `/api/scraper/google-quota` | Monthly Places API usage |
| `POST` | `/api/email/draft` | Draft email with Claude |
| `POST` | `/api/email/send` | Send email via Gmail |

---

## Business Categories

Hotels & Resorts · Resorts · Ski Resorts · Amusement Parks · Water Parks · Campgrounds · Golf & Country Clubs · Event Venues · Summer Camps · Vacation Lodges · Beach Clubs · Theme Parks · **Restaurants**

---

## Development

**Backend only:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Frontend only:**
```bash
cd frontend
npm run dev        # http://localhost:5173
```

**Build .exe for distribution:**
```bash
build.bat          # outputs dist/GAVA-CRM.exe
```

---

## Database

SQLite file is created automatically at `backend/gava.db` on first run. Schema is managed via SQLAlchemy with inline migrations in `main.py` for backward compatibility.

**Tables:** `leads` · `email_logs` · `scrape_jobs`

---

## Lead Pipeline

```
new → contacted → replied → meeting_booked → converted
                                           → archived (any stage)
```

---

## License

Private — GAVA Recruiting internal tool.

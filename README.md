# Nex-Lyon Real Estate Analyzer

Automated Python tool that **scrapes**, **stores**, and **analyzes** real estate listings in Lyon, France — with a **React dashboard**, **PDF reports**, and **Google Sheets** sync.

**Built By Mithun Miras**

---

## Features

| Feature | Details |
|---------|---------|
| **Live Scraping** | SerpAPI (Google Search API) with randomized queries — fresh data every run |
| **React Dashboard** | Interactive web UI with charts, scores, and undervalued property cards |
| **PDF & TXT Reports** | Downloadable investment reports from the dashboard |
| **Database** | SQLite with price tracking and session history |
| **AI Analysis** | Google Gemini generates BUY/HOLD/AVOID verdicts for top opportunities |
| **Rule-Based Scoring** | Investment score (1-10) based on price, yield, DPE, and ROI |
| **Google Sheets Sync** | Each run creates a new tab with Properties + Analysis + Run Info |
| **Undervalued Detection** | Flags properties below market price/m² with renovation upside |

---

## Live Demo

**Try it now:** [https://nex-lyon-real-estate-automated-analyzer-1.onrender.com](https://nex-lyon-real-estate-automated-analyzer-1.onrender.com/)

> **Note:** Run timestamps in the deployed version are in **UTC**. The first request may take ~30 seconds as Render spins up the free-tier instance.

---

## Manual Setup (Local)

If you prefer to run it locally, follow the steps below.

### Prerequisites

- **Python 3.9+** ([python.org/downloads](https://www.python.org/downloads/))
- **Node.js 18+** ([nodejs.org](https://nodejs.org)) — for the React frontend
- **SerpAPI Key** ([serpapi.com](https://serpapi.com)) — required for live data

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/Mithunmiras/Nex-Lyon-Real-Estate-Automated-Analyzer.git
cd Nex-Lyon-Real-Estate-Automated-Analyzer

# 2. Create & activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Build the React frontend
cd frontend && npm install && npm run build && cd ..

# 5. Set up environment variables
cp .env.example .env
# Edit .env and add your API keys (see below)

# 6. Run the web dashboard
python server.py
# Open http://localhost:5000

# OR run via CLI
python main.py
```

### Required Environment Variables

Create a `.env` file with:

| Key | Purpose | Where to get it |
|-----|---------|-----------------|
| `SERPAPI_KEY` | **Required** — Live web scraping | [serpapi.com](https://serpapi.com) (free tier: 100 searches/mo) |
| `GEMINI_API_KEY` | AI investment insights | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (free) |
| `GOOGLE_SHEET_ID` | Cloud data sync | See Google Sheets setup below |
| `GOOGLE_CREDENTIALS_FILE` | Service account auth | See Google Sheets setup below |

### Optional: Google Sheets Sync

Each run creates a **new tab** in your Google Sheet with all data (Properties, Analysis, Run Info) combined.

**One-time setup (5 minutes):**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Google Sheets API** and **Google Drive API**
3. **IAM & Admin → Service Accounts** → Create → **Keys → Add Key → JSON** → download
4. Save as `credentials.json` in the project folder
5. Create a Google Sheet → copy the **Sheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_THE_SHEET_ID/edit
   ```
6. Share the Sheet with the **service account email** (from `credentials.json`) as **Editor**
7. Add to `.env`:
   ```
   GOOGLE_SHEET_ID=your_sheet_id_here
   GOOGLE_CREDENTIALS_FILE=credentials.json
   ```

For deployed environments (e.g., Render), set `GOOGLE_CREDENTIALS_JSON` as a base64-encoded env var instead of using the file.

---

## How It Works

### Architecture

```
server.py          -> Flask web server + API (run this for dashboard)
main.py            -> CLI entry point (alternative to server)
  |-- config.py    -> Settings & Lyon market reference data
  |-- database.py  -> SQLite with session tracking & clear-on-run
  |-- scraper.py   -> SerpAPI live scraping (randomized queries, no cache)
  |-- analyzer.py  -> Rule-based scoring + Gemini AI verdicts
  |-- sheets.py    -> Google Sheets sync (new tab per run)
frontend/          -> React + Vite + Recharts dashboard
```

### Pipeline

```
[1/4] Database Setup
  -> Creates SQLite schema → clears old data for fresh run

[2/4] Live Data Scraping
  -> Randomized SerpAPI queries across arrondissements, room types, price ranges
  -> Searches SeLoger, LeBonCoin, BienIci, PAP, Logic-Immo via Google
  -> Parses price, size, arrondissement, rooms, DPE from results

[3/4] Investment Analysis
  -> Rule-based: price vs market, rental yield, renovation ROI, DPE impact
  -> AI (optional): Gemini generates BUY/HOLD/AVOID for top opportunities
  -> Generates downloadable report (TXT + PDF)

[4/4] Google Sheets Sync
  -> Creates a new tab with timestamp (e.g., "Run 2026-02-16 17:30")
  -> Contains Run Info + Properties + Analysis in one sheet
  -> Previous run tabs are preserved for history
```

### Anti-Scraping Strategy

We use **SerpAPI** — a legitimate Google Search API that:

- Solves CAPTCHAs automatically
- Rotates IPs across data centers
- Handles rate limiting and retries
- Returns structured JSON from Google Search results
- `no_cache: true` ensures fresh results each run

Queries are **randomized** each run (different arrondissements, room types, price ranges, listing sites) to maximize data variety.

### Data Freshness

Each run **clears the database** and scrapes fresh data from the API. No stale or synthetic data is used. Previous results are preserved in Google Sheets tabs for historical comparison.

### Investment Scoring (1-10)

The score factors in:

| Factor | Impact |
|--------|--------|
| Price/m² below market average | +1.5 to +2.5 |
| DPE E/F/G with renovation upside | +1.5 |
| DPE A/B (already efficient) | +0.5 |
| High-yield area (>5%) | +0.5 |
| Strong 5yr ROI (>30%) | +1.0 |
| Overpriced vs market | -1.0 to -2.0 |

---

## Output

The program generates:

1. **React Dashboard** at `http://localhost:5000` with charts, scores, and property cards
2. **PDF Report** downloadable from the dashboard
3. **TXT Report** (`report_YYYY-MM-DD.txt`) saved to the project folder
4. **Google Sheets** — new tab per run with all data combined
5. **SQLite Database** (`lyon_real_estate.db`) for the current run

---

## File Structure

```
nex_lyon_analyzer/
|-- server.py            # Flask API + web server (run this)
|-- main.py              # CLI entry point
|-- config.py            # Configuration & market data
|-- database.py          # Database operations
|-- scraper.py           # Live data collection (SerpAPI)
|-- analyzer.py          # Investment analysis + scoring
|-- sheets.py            # Google Sheets sync
|-- requirements.txt     # Python dependencies
|-- .env                 # API keys
|-- .env.example         # API key template
|-- credentials.json     # Google service account key
|-- frontend/            # React + Vite dashboard
|   |-- src/App.jsx      # Main dashboard component
|   |-- dist/            # Built frontend (served by Flask)
|-- lyon_real_estate.db  # Database (auto-created)
|-- report_*.txt         # Generated text reports
|-- report_*.pdf         # Generated PDF reports
```

---

## Deployment (Render)

1. Push code to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Connect your GitHub repo
4. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn server:app -b 0.0.0.0:$PORT --timeout 120`
5. Add environment variables: `SERPAPI_KEY`, `GEMINI_API_KEY`, `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_JSON` (base64-encoded)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `pip` not recognized | Use `python -m pip install -r requirements.txt` |
| `python` not recognized | Try `python3`, or check Python is in your PATH |
| ModuleNotFoundError | Activate the venv first: `.venv\Scripts\activate` |
| Same data every run | Fixed — DB is cleared + queries are randomized + `no_cache` enabled |
| SerpAPI returns 0 results | Check your API key and quota at [serpapi.com/manage-api-key](https://serpapi.com/manage-api-key) |
| Gemini API error | AI insights are skipped gracefully; rule-based analysis still runs |
| PDF download shows 404 | Run an analysis first — reports are generated during the pipeline |
| Google Sheets not syncing | Check `GOOGLE_SHEET_ID` and credentials in `.env` |

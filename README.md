# Nex-Lyon Real Estate Analyzer

Automated Python tool that **scrapes**, **stores**, and **analyzes** real estate listings in Lyon, France.

---

## Features

| Feature | Details |
|---------|---------|
| **Automated Scraping** | SerpAPI (legitimate Google Search API) - bypasses anti-scraping via CAPTCHA solving, IP rotation, rate-limit handling |
| **Database** | SQLite with historical price tracking across multiple runs |
| **AI Analysis** | Google Gemini generates investment verdicts for top opportunities |
| **Rule-Based Scoring** | Works fully offline with no API keys (demo mode) |
| **Undervalued Detection** | Flags properties below market price/m² with renovation upside |

---

## One-Click Setup (SOP)

### Prerequisites

- **Python 3.9+** installed ([python.org/downloads](https://www.python.org/downloads/))

### Steps

```bash
# 1. Open a terminal in the project folder

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
#    Windows:
.venv\Scripts\activate
#    macOS / Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run
python main.py
```

**That's it.** No API keys are required - the program runs in demo mode with 20 curated Lyon properties.

### Optional: Enable Live Data & AI

Copy `.env.example` to `.env` and add your keys:

```bash
cp .env.example .env
```

| Key | Purpose | Where to get it |
|-----|---------|-----------------|
| `SERPAPI_KEY` | Live web scraping | [serpapi.com](https://serpapi.com) (free tier available) |
| `GEMINI_API_KEY` | AI investment insights | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (free) |
| `GOOGLE_SHEET_ID` | Cloud data sync | See Google Sheets setup below |
| `GOOGLE_CREDENTIALS_FILE` | Service account auth | See Google Sheets setup below |

### Optional: Enable Google Sheets Sync

Data is automatically synced to a Google Sheet (3 tabs: Properties, Analysis, History).

**One-time setup (5 minutes):**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project (or select existing) → Enable **Google Sheets API** and **Google Drive API**
3. Go to **IAM & Admin → Service Accounts** → Create a service account
4. Click the service account → **Keys** tab → **Add Key → JSON** → download the file
5. Rename it to `credentials.json` and place it in the project folder
6. Create a new Google Sheet → copy the **Sheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_THE_SHEET_ID/edit
   ```
7. Share the Google Sheet with the **service account email** (found in `credentials.json` under `client_email`) as **Editor**
8. Add to your `.env`:
   ```
   GOOGLE_SHEET_ID=your_sheet_id_here
   GOOGLE_CREDENTIALS_FILE=credentials.json
   ```

The program creates 3 worksheets automatically:
- **Properties** — all scraped listings with prices, sizes, DPE, timestamps
- **Analysis** — scored & ranked investment analysis with ROI calculations
- **History** — run log for tracking data growth over time

---

## How It Works

### Architecture

```
main.py          -> Orchestrator (run this)
  |-- config.py    -> Settings, market data, demo fixtures
  |-- database.py  -> SQLite with historical tracking
  |-- scraper.py   -> SerpAPI live scraping + demo mode
  |-- analyzer.py  -> Rule-based metrics + Gemini AI insights
  |-- sheets.py    -> Google Sheets sync (Properties, Analysis, History)
```

### Pipeline

```
[1/4] Database Setup
  -> Creates/upgrades SQLite schema (properties, price_history, analyses, sessions)

[2/4] Data Scraping
  -> If SERPAPI_KEY: searches Google for SeLoger Lyon listings, parses price/size/DPE
  -> If no key:     loads 20 curated demo properties across all 9 arrondissements

[3/4] Investment Analysis
  -> Rule-based: price vs market avg, rental yield, renovation ROI, DPE impact
  -> AI (optional): Gemini generates BUY/HOLD/AVOID verdicts for top opportunities
  -> Saves all results to DB + generates report file

[4/4] Google Sheets Sync
  -> Exports properties, analysis rankings, and run history to Google Sheets
  -> Skipped gracefully if no credentials configured
```

### Anti-Scraping Strategy

Instead of scraping websites directly (which triggers CAPTCHAs and IP bans), we use **SerpAPI** - a legitimate API service that:

- Solves CAPTCHAs automatically
- Rotates IPs across data centers
- Handles rate limiting and retries
- Returns structured JSON from Google Search results

This is the industry-standard legal approach to web data collection.

### Historical Tracking

Each run creates a **scrape session**. When a property is seen again:

- Its `last_seen` timestamp is updated
- Price changes are recorded in `price_history`
- Old and new analyses are preserved for trend comparison

Run `python main.py` weekly to build a historical dataset.

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

1. **Console report** with market overview, rankings, and undervalued highlights
2. **`report_YYYY-MM-DD.txt`** saved to the project folder
3. **SQLite database** (`lyon_real_estate.db`) with all data for further analysis

---

## File Structure

```
nex_lyon_analyzer/
|-- main.py              # Entry point
|-- config.py            # Configuration & market data
|-- database.py          # Database operations
|-- scraper.py           # Data collection
|-- analyzer.py          # Investment analysis
|-- sheets.py            # Google Sheets sync
|-- requirements.txt     # Python dependencies
|-- .env                 # Your API keys (gitignored)
|-- .env.example         # API key template
|-- credentials.json     # Google service account key (gitignored)
|-- README.md            # This file
|-- lyon_real_estate.db  # Database (auto-created)
|-- report_*.txt         # Generated reports
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `pip` not recognized | Use `python -m pip install -r requirements.txt` |
| `python` not recognized | Try `python3`, or check Python is in your PATH |
| ModuleNotFoundError | Activate the venv first: `.venv\Scripts\activate` |
| Encoding error on Windows | Update to Windows Terminal; the code handles this automatically |
| SerpAPI returns 0 results | Normal - it falls back to demo data. Check your API key quota |
| Gemini API error | AI insights are skipped gracefully; rule-based analysis still runs |

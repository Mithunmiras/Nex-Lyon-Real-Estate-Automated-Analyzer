"""
Nex-Lyon Real Estate Analyzer - Google Sheets Integration

Syncs SQLite data to a Google Sheet for cloud access and live dashboards.

Setup (one-time):
  1. Go to https://console.cloud.google.com
  2. Create a project (or use existing)
  3. Enable "Google Sheets API" and "Google Drive API"
  4. Create a Service Account → download JSON key → save as credentials.json
  5. Create a Google Sheet → share it with the service account email (Editor)
  6. Copy the Sheet ID from the URL and put it in .env as GOOGLE_SHEET_ID
"""

import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE
from database import get_all_properties, get_session_count, get_first_session_date


# ─── Auth ──────────────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_client() -> gspread.Client:
    """Authenticate with Google via service account credentials."""
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def _ensure_worksheet(spreadsheet: gspread.Spreadsheet, title: str, headers: list[str]) -> gspread.Worksheet:
    """Get or create a worksheet with the given headers."""
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=500, cols=len(headers))

    # Always update headers (row 1)
    ws.update([headers], "A1")

    # Bold + freeze header row
    ws.format("A1:Z1", {"textFormat": {"bold": True}})
    ws.freeze(rows=1)

    return ws


# ─── Sync Functions ────────────────────────────────────────────────────────────

def sync_properties(spreadsheet: gspread.Spreadsheet, properties: list[dict]):
    """Write all properties to the 'Properties' sheet."""
    headers = [
        "ID", "Title", "Price (EUR)", "Arrondissement", "Size (m²)",
        "Rooms", "DPE", "Price/m² (EUR)", "Description", "URL",
        "First Seen", "Last Seen", "Active",
    ]
    ws = _ensure_worksheet(spreadsheet, "Properties", headers)

    rows = []
    for p in properties:
        rows.append([
            p.get("id", ""),
            p.get("title", ""),
            p.get("price", 0),
            p.get("arrondissement", ""),
            p.get("size", 0),
            p.get("rooms", 0),
            p.get("dpe", ""),
            round(p.get("price_per_m2", 0)),
            (p.get("description") or "")[:200],
            p.get("url", ""),
            (p.get("first_seen") or "")[:19],
            (p.get("last_seen") or "")[:19],
            "Yes" if p.get("is_active") else "No",
        ])

    if rows:
        # Clear old data (keep header), then write
        ws.batch_clear([f"A2:M{ws.row_count}"])
        ws.update(rows, f"A2:M{1 + len(rows)}")

    return len(rows)


def sync_analyses(spreadsheet: gspread.Spreadsheet, properties: list[dict], all_metrics: list[dict]):
    """Write the analysis results to the 'Analysis' sheet."""
    headers = [
        "ID", "Title", "Arrondissement", "Score", "Verdict",
        "Price (EUR)", "Price/m²", "Market Avg/m²", "vs Market %",
        "Monthly Rent", "Yield %", "5yr ROI %",
        "Reno Cost", "Post-Reno Value", "Capital Gain",
        "DPE", "Undervalued?",
    ]
    ws = _ensure_worksheet(spreadsheet, "Analysis", headers)

    # Sort by score descending
    ranked = sorted(
        zip(properties, all_metrics), key=lambda x: x[1]["score"], reverse=True
    )

    rows = []
    for p, m in ranked:
        score = m["score"]
        if score >= 7:
            verdict = "BUY"
        elif score >= 5:
            verdict = "HOLD"
        else:
            verdict = "AVOID"

        rows.append([
            p.get("id", ""),
            p.get("title", ""),
            p.get("arrondissement", ""),
            score,
            verdict,
            p.get("price", 0),
            m["price_m2"],
            m["market_avg_m2"],
            m["price_vs_market_pct"],
            m["monthly_rent"],
            m["rental_yield_pct"],
            m["roi_5yr"],
            m["reno_cost"],
            m["post_reno_value"],
            m["capital_gain"],
            p.get("dpe", ""),
            "YES" if m["is_undervalued"] else "",
        ])

    if rows:
        ws.batch_clear([f"A2:Q{ws.row_count}"])
        ws.update(rows, f"A2:Q{1 + len(rows)}")

    return len(rows)


def sync_history(spreadsheet: gspread.Spreadsheet):
    """Write a run-history log to the 'History' sheet."""
    headers = ["Run Date", "Total Properties", "Sessions", "Tracking Since"]
    ws = _ensure_worksheet(spreadsheet, "History", headers)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    sessions = get_session_count()
    first = get_first_session_date()
    first_str = first[:10] if first else now[:10]
    total = len(get_all_properties())

    # Append a new row (don't overwrite previous runs)
    existing = ws.get_all_values()
    next_row = len(existing) + 1
    ws.update([[now, total, sessions, first_str]], f"A{next_row}")


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def sync_to_sheets(properties: list[dict] = None, all_metrics: list[dict] = None) -> str:
    """
    Sync all data to Google Sheets.
    Returns a status message.
    """
    if not GOOGLE_SHEET_ID:
        return "  Skipped: No GOOGLE_SHEET_ID in .env"
    if not GOOGLE_CREDENTIALS_FILE:
        return "  Skipped: No GOOGLE_CREDENTIALS_FILE in .env"

    import os
    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        return f"  Skipped: Credentials file not found at {GOOGLE_CREDENTIALS_FILE}"

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        # If properties not passed, load from DB
        if properties is None:
            properties = get_all_properties()

        prop_count = sync_properties(spreadsheet, properties)

        if all_metrics:
            sync_analyses(spreadsheet, properties, all_metrics)

        sync_history(spreadsheet)

        sheet_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
        return (
            f"  Synced {prop_count} properties to Google Sheets\n"
            f"  Sheet: {sheet_url}"
        )
    except Exception as e:
        return f"  Google Sheets sync error: {e}"

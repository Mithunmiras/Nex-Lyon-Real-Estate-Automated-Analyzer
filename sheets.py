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

import json
import base64
import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE, GOOGLE_CREDENTIALS_JSON
from database import get_all_properties, get_session_count, get_first_session_date


# ─── Auth ──────────────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_client() -> gspread.Client:
    """Authenticate with Google via service account credentials.
    Supports: env var (base64 or raw JSON) or local file."""
    import os

    # Priority 1: GOOGLE_CREDENTIALS_JSON env var (for deployed environments)
    if GOOGLE_CREDENTIALS_JSON:
        try:
            # Try base64 first
            info = json.loads(base64.b64decode(GOOGLE_CREDENTIALS_JSON))
        except Exception:
            # Try raw JSON string
            info = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return gspread.authorize(creds)

    # Priority 2: credentials file (for local development)
    if os.path.exists(GOOGLE_CREDENTIALS_FILE):
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
        return gspread.authorize(creds)

    raise FileNotFoundError(
        "No Google credentials found. Set GOOGLE_CREDENTIALS_JSON env var "
        "or place credentials.json in the project folder."
    )


def _col_letter(n: int) -> str:
    """Convert 1-based column number to letter(s): 1->A, 26->Z, 27->AA."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _build_single_sheet(
    spreadsheet: gspread.Spreadsheet,
    properties: list[dict],
    all_metrics: list[dict] | None,
) -> tuple[gspread.Worksheet, int]:
    """
    Create a NEW worksheet named with the current timestamp.
    Write all data (Properties + Analysis + Run Info) into one sheet.
    Returns (worksheet, property_count).
    """
    now = datetime.datetime.now()
    tab_title = f"Run {now.strftime('%Y-%m-%d %H:%M')}"

    # Estimate rows needed
    prop_count = len(properties)
    analysis_count = len(all_metrics) if all_metrics else 0
    total_rows = prop_count + analysis_count + 20  # extra for headers/spacing
    total_cols = 17  # max columns across all sections

    ws = spreadsheet.add_worksheet(title=tab_title, rows=max(total_rows, 50), cols=total_cols)

    all_rows = []  # collect everything, write in one batch
    bold_rows = []  # track which rows to bold (0-indexed)
    current_row = 1

    # ── Section 1: Run Info ────────────────────────────────────────────────
    sessions = get_session_count()
    first = get_first_session_date()
    first_str = first[:10] if first else now.strftime("%Y-%m-%d")

    all_rows.append(["RUN INFORMATION", "", "", ""])
    bold_rows.append(current_row)
    current_row += 1

    all_rows.append(["Run Date", "Total Properties", "Sessions", "Tracking Since"])
    bold_rows.append(current_row)
    current_row += 1

    all_rows.append([now.strftime("%Y-%m-%d %H:%M"), prop_count, sessions, first_str])
    current_row += 1

    # Blank separator row
    all_rows.append([""])
    current_row += 1

    # ── Section 2: Properties ──────────────────────────────────────────────
    prop_headers = [
        "PROPERTIES", "", "", "", "", "", "", "", "", "", "", "", "",
    ]
    all_rows.append(prop_headers)
    bold_rows.append(current_row)
    current_row += 1

    prop_col_headers = [
        "ID", "Title", "Price (EUR)", "Arrondissement", "Size (m²)",
        "Rooms", "DPE", "Price/m² (EUR)", "Description", "URL",
        "First Seen", "Last Seen", "Active",
    ]
    all_rows.append(prop_col_headers)
    bold_rows.append(current_row)
    current_row += 1

    for p in properties:
        all_rows.append([
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
        current_row += 1

    # Blank separator row
    all_rows.append([""])
    current_row += 1

    # ── Section 3: Analysis ────────────────────────────────────────────────
    if all_metrics and properties:
        all_rows.append(["INVESTMENT ANALYSIS", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
        bold_rows.append(current_row)
        current_row += 1

        analysis_headers = [
            "ID", "Title", "Arrondissement", "Score", "Verdict",
            "Price (EUR)", "Price/m²", "Market Avg/m²", "vs Market %",
            "Monthly Rent", "Yield %", "5yr ROI %",
            "Reno Cost", "Post-Reno Value", "Capital Gain",
            "DPE", "Undervalued?",
        ]
        all_rows.append(analysis_headers)
        bold_rows.append(current_row)
        current_row += 1

        ranked = sorted(
            zip(properties, all_metrics), key=lambda x: x[1]["score"], reverse=True
        )

        for p, m in ranked:
            score = m["score"]
            if score >= 7:
                verdict = "BUY"
            elif score >= 5:
                verdict = "HOLD"
            else:
                verdict = "AVOID"

            all_rows.append([
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
            current_row += 1

    # ── Write everything in one batch ──────────────────────────────────────
    end_col = _col_letter(total_cols)
    ws.update(all_rows, f"A1:{end_col}{len(all_rows)}")

    # Bold section headers and column headers
    for row_num in bold_rows:
        ws.format(f"A{row_num}:{end_col}{row_num}", {"textFormat": {"bold": True}})

    # Freeze first row
    ws.freeze(rows=1)

    return ws, prop_count


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def sync_to_sheets(properties: list[dict] = None, all_metrics: list[dict] = None) -> str:
    """
    Sync all data to Google Sheets.
    Each run creates a NEW worksheet tab named with the timestamp.
    All data (Properties + Analysis + Run Info) goes into that single tab.
    Returns a status message.
    """
    if not GOOGLE_SHEET_ID:
        return "  Skipped: No GOOGLE_SHEET_ID in .env"

    import os
    if not GOOGLE_CREDENTIALS_JSON and not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        return "  Skipped: No credentials (set GOOGLE_CREDENTIALS_JSON env var or add credentials.json)"

    try:
        client = _get_client()
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

        # If properties not passed, load from DB
        if properties is None:
            properties = get_all_properties()

        ws, prop_count = _build_single_sheet(spreadsheet, properties, all_metrics)

        sheet_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
        return (
            f"  Synced {prop_count} properties to Google Sheets (tab: {ws.title})\n"
            f"  Sheet: {sheet_url}"
        )
    except Exception as e:
        return f"  Google Sheets sync error: {e}"

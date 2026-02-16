"""
Nex-Lyon Real Estate Analyzer - Configuration
Settings and Lyon market reference data.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys ──────────────────────────────────────────────────────────────────
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─── Google Sheets ─────────────────────────────────────────────────────────────
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")  # base64 or raw JSON

# ─── Database ──────────────────────────────────────────────────────────────────
DB_NAME = "lyon_real_estate.db"

# ─── Lyon Market Reference Data (2025-2026 estimates) ─────────────────────────
# Source: avg observed prices and rental yields per arrondissement
LYON_MARKET = {
    "Lyon 1er": {"avg_price_m2": 4800, "rental_yield_pct": 3.8},
    "Lyon 2e":  {"avg_price_m2": 5300, "rental_yield_pct": 3.5},
    "Lyon 3e":  {"avg_price_m2": 4300, "rental_yield_pct": 4.5},
    "Lyon 4e":  {"avg_price_m2": 4800, "rental_yield_pct": 4.0},
    "Lyon 5e":  {"avg_price_m2": 4300, "rental_yield_pct": 4.2},
    "Lyon 6e":  {"avg_price_m2": 6000, "rental_yield_pct": 3.3},
    "Lyon 7e":  {"avg_price_m2": 4300, "rental_yield_pct": 4.8},
    "Lyon 8e":  {"avg_price_m2": 3700, "rental_yield_pct": 5.5},
    "Lyon 9e":  {"avg_price_m2": 3400, "rental_yield_pct": 5.8},
}

# ─── DPE Energy Ratings ───────────────────────────────────────────────────────
# value_factor  : multiplier on property value relative to DPE C baseline
# energy_cost_yr: estimated annual energy cost in EUR
# reno_cost_m2  : estimated cost per m2 to renovate to DPE B level
DPE = {
    "A": {"label": "Excellent",  "value_factor": 1.10, "energy_cost_yr": 250,  "reno_cost_m2": 0},
    "B": {"label": "Very Good",  "value_factor": 1.05, "energy_cost_yr": 500,  "reno_cost_m2": 0},
    "C": {"label": "Good",       "value_factor": 1.00, "energy_cost_yr": 750,  "reno_cost_m2": 100},
    "D": {"label": "Average",    "value_factor": 0.95, "energy_cost_yr": 1100, "reno_cost_m2": 250},
    "E": {"label": "Poor",       "value_factor": 0.88, "energy_cost_yr": 1600, "reno_cost_m2": 450},
    "F": {"label": "Very Poor",  "value_factor": 0.80, "energy_cost_yr": 2200, "reno_cost_m2": 650},
    "G": {"label": "Critical",   "value_factor": 0.70, "energy_cost_yr": 3000, "reno_cost_m2": 900},
}



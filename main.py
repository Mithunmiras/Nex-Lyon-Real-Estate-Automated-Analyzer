"""
Nex-Lyon Real Estate Analyzer
Automated scraping, storage, and AI analysis of Lyon real estate.

Usage:  python main.py
"""

import sys
import datetime
from database import create_db
from scraper import scrape
from analyzer import analyze
from sheets import sync_to_sheets

BANNER = r"""
 _   _              _
| \ | | _____  __  | |    _   _  ___  _ __
|  \| |/ _ \ \/ /  | |   | | | |/ _ \| '_ \
| |\  |  __/>  <   | |___| |_| | (_) | | | |
|_| \_|\___/_/\_\  |______\__, |\___/|_| |_|
  Real Estate Analyzer    |___/  v2.0
"""


def main():
    # Ensure French chars print correctly on Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(BANNER)

    # Step 1 ─ Database
    print("[1/4] Setting up database...")
    create_db()
    print("  Database ready.\n")

    # Step 2 ─ Scrape
    print("[2/4] Scraping property data...")
    count = scrape()
    if count > 0:
        print(f"  {count} new properties loaded.\n")
    else:
        print("  Properties already in database (0 new).\n")

    # Step 3 ─ Analyze
    print("[3/4] Running investment analysis...")
    report, properties, metrics = analyze()

    # Step 4 ─ Google Sheets
    print("[4/4] Syncing to Google Sheets...")
    sheets_status = sync_to_sheets(properties, metrics)
    print(sheets_status + "\n")

    # Print to console
    print("\n")
    print(report)

    # Save to file
    filename = f"report_{datetime.date.today()}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved to: {filename}")


if __name__ == "__main__":
    main()

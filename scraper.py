"""
Nex-Lyon Real Estate Analyzer - Scraper

Strategy for bypassing anti-scraping mechanisms:
  We use SerpAPI (https://serpapi.com), a legitimate Google Search API that
  handles CAPTCHAs, IP rotation, and rate-limiting behind the scenes.
  This is the industry-standard legal approach for web data collection.

Falls back to curated demo data when no API key is available.
"""

import re
import requests
from config import SERPAPI_KEY, DEMO_LISTINGS, LYON_MARKET
from database import create_session, update_session_count, upsert_property


# ─── Text Parsers ──────────────────────────────────────────────────────────────

def _parse_price(text: str):
    """Extract a price in EUR from free text.  250 000 EUR / 250,000 / etc."""
    if not text:
        return None
    for pattern in [
        r"(\d[\d\s\.]{2,})\s*(?:EUR|euros?|\u20ac)",
        r"(?:EUR|\u20ac)\s*(\d[\d\s\.]{2,})",
        r"(\d{5,})\s*(?:EUR|euros?|\u20ac)",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            digits = m.group(1).replace(" ", "").replace(".", "").replace(",", "")
            try:
                price = int(digits)
                if 30_000 < price < 5_000_000:
                    return price
            except ValueError:
                continue
    return None


def _parse_size(text: str):
    """Extract size in m2 from free text."""
    if not text:
        return None
    for pattern in [r"(\d+(?:[.,]\d+)?)\s*m[2\u00b2]", r"(\d+(?:[.,]\d+)?)\s*m\b"]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            size = float(m.group(1).replace(",", "."))
            if 8 < size < 500:
                return size
    return None


def _parse_arrondissement(text: str):
    """Extract Lyon arrondissement (1er-9e) from free text or postal code."""
    if not text:
        return None
    for pattern in [
        r"Lyon\s*(\d{1,2})(?:e|er|eme|[e\u00e8]me)",
        r"690(\d{2})",
        r"Lyon\s+(\d)\b",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            n = int(m.group(1).lstrip("0") or "0")
            if 1 <= n <= 9:
                return f"Lyon {n}{'er' if n == 1 else 'e'}"
    return None


def _parse_rooms(text: str):
    """Extract room count from T3/F3/3 pieces patterns."""
    if not text:
        return None
    m = re.search(r"[TF](\d)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d)\s*pi[e\u00e8]ces?", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _parse_dpe(text: str):
    """Extract DPE rating (A-G)."""
    if not text:
        return None
    m = re.search(r"DPE\s*[:\s]*([A-G])", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


# ─── Live Scraping via SerpAPI ─────────────────────────────────────────────────

def scrape_live() -> int:
    """
    Query SerpAPI (Google Search) for SeLoger Lyon listings.
    Parses price, size, arrondissement, DPE from result titles & snippets.
    Returns number of NEW properties inserted.
    """
    if not SERPAPI_KEY:
        raise ValueError("No SERPAPI_KEY configured")

    session_id = create_session("serpapi", "live")
    inserted = 0

    queries = [
        "site:seloger.com appartement achat Lyon",
        "site:seloger.com vente appartement Lyon prix",
        "appartement a vendre Lyon seloger",
    ]

    for query in queries:
        try:
            resp = requests.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google",
                    "q": query,
                    "api_key": SERPAPI_KEY,
                    "num": 10,
                    "hl": "fr",
                    "gl": "fr",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"    Warning: query failed - {e}")
            continue

        for result in data.get("organic_results", []):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            link = result.get("link", "")
            combined = f"{title} {snippet}"

            arrond = _parse_arrondissement(combined)
            if not arrond:
                continue  # skip if we can't place it in Lyon

            price = _parse_price(combined)
            size = _parse_size(combined)
            rooms = _parse_rooms(combined)
            dpe = _parse_dpe(combined)

            # Fallback estimates from market averages
            market = LYON_MARKET.get(arrond, {})
            avg_m2 = market.get("avg_price_m2", 4300)
            if not price and size:
                price = int(size * avg_m2)
            if not size and price:
                size = round(price / avg_m2, 1)
            price = price or 250000
            size = size or 55
            rooms = rooms or 2
            dpe = dpe or "D"

            prop = {
                "title": title[:120],
                "price": price,
                "arrondissement": arrond,
                "size": size,
                "rooms": rooms,
                "dpe": dpe,
                "description": snippet[:300],
                "url": link,
                "price_per_m2": price / size if size else 0,
            }
            _, is_new = upsert_property(prop, session_id)
            if is_new:
                inserted += 1
                print(f"    + {title[:60]}")

    update_session_count(session_id, inserted)
    return inserted


# ─── Demo Mode ─────────────────────────────────────────────────────────────────

def scrape_demo() -> int:
    """Load curated demo listings into the database. Returns new property count."""
    session_id = create_session("demo", "demo")
    inserted = 0

    for item in DEMO_LISTINGS:
        prop = {
            "title": item["title"],
            "price": item["price"],
            "arrondissement": item["arrondissement"],
            "size": item["size"],
            "rooms": item["rooms"],
            "dpe": item["dpe"],
            "description": item["description"],
            "url": "",
            "price_per_m2": item["price"] / item["size"],
        }
        _, is_new = upsert_property(prop, session_id)
        if is_new:
            inserted += 1
            print(f"    + {item['title']}")

    update_session_count(session_id, inserted)
    return inserted


# ─── Entry Point ───────────────────────────────────────────────────────────────

def scrape() -> int:
    """Try live scraping; fall back to demo data on failure or missing key."""
    if SERPAPI_KEY:
        print("  SerpAPI key detected - attempting live scrape...")
        try:
            count = scrape_live()
            if count > 0:
                return count
            print("  No new results from live scrape, adding demo data...")
        except Exception as e:
            print(f"  Live scrape error: {e}")
            print("  Falling back to demo data...")
    else:
        print("  No SerpAPI key - using demo data (set SERPAPI_KEY in .env for live)")

    return scrape_demo()

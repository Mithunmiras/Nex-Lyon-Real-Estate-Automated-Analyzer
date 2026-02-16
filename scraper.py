"""
Nex-Lyon Real Estate Analyzer - Scraper

Strategy for bypassing anti-scraping mechanisms:
  We use SerpAPI (https://serpapi.com), a legitimate Google Search API that
  handles CAPTCHAs, IP rotation, and rate-limiting behind the scenes.
  This is the industry-standard legal approach for web data collection.

Requires a valid SERPAPI_KEY in .env to function.
"""

import re
import random
import requests
from config import SERPAPI_KEY, LYON_MARKET
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
    Query SerpAPI (Google Search) for Lyon property listings.
    Uses randomized, varied queries each run to get different results.
    Returns number of NEW properties inserted.
    """
    if not SERPAPI_KEY:
        raise ValueError("No SERPAPI_KEY configured")

    session_id = create_session("serpapi", "live")
    inserted = 0

    # Build diverse queries — pick random arrondissements, price ranges, room types
    arrondissements = ["Lyon 1er", "Lyon 2eme", "Lyon 3eme", "Lyon 4eme",
                       "Lyon 5eme", "Lyon 6eme", "Lyon 7eme", "Lyon 8eme", "Lyon 9eme"]
    room_types = ["T2", "T3", "T4", "studio", "T5"]
    price_ranges = ["moins de 200000", "200000 300000", "300000 500000", "plus de 400000"]
    sites = ["site:seloger.com", "site:leboncoin.fr", "site:bien-ici.fr",
             "site:logic-immo.com", "site:pap.fr"]

    # Always include a few broad queries
    base_queries = [
        f"{random.choice(sites)} appartement achat {random.choice(arrondissements)}",
        f"{random.choice(sites)} vente appartement Lyon {random.choice(room_types)}",
        f"appartement a vendre Lyon {random.choice(arrondissements)} prix",
    ]

    # Add targeted queries with random parameters
    extra_queries = [
        f"{random.choice(sites)} {random.choice(room_types)} Lyon {random.choice(arrondissements)}",
        f"achat appartement Lyon {random.choice(price_ranges)} euros",
        f"{random.choice(sites)} appartement Lyon DPE {random.choice(['A','B','C','D','E'])}",
        f"vente immobilier Lyon {random.choice(arrondissements)} {random.choice(room_types)} {random.choice(price_ranges)}",
        f"appartement {random.choice(room_types)} a vendre {random.choice(arrondissements)} 2026",
        f"{random.choice(sites)} Lyon appartement {random.randint(30,100)}m2",
    ]

    # Pick 5 queries total (3 base + 2 random extras) to stay within API limits
    queries = base_queries + random.sample(extra_queries, min(2, len(extra_queries)))
    random.shuffle(queries)

    print(f"    Running {len(queries)} search queries...")

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
                    "no_cache": "true",
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


# ─── Entry Point ───────────────────────────────────────────────────────────────

def scrape() -> int:
    """Scrape live data via SerpAPI. Requires SERPAPI_KEY in .env."""
    if not SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY is required in .env - no demo/synthetic data available")

    print("  SerpAPI key detected - scraping live data...")
    count = scrape_live()
    print(f"  Scrape complete: {count} new properties found")
    return count

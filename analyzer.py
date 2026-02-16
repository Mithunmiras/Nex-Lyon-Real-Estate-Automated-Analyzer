"""
Nex-Lyon Real Estate Analyzer - Investment Analysis

Two-layer analysis:
  1. Rule-based metrics (always runs, no API needed)
  2. Gemini AI insights (only for top candidates, requires GEMINI_API_KEY)
"""

import time
import datetime
from config import GEMINI_API_KEY, LYON_MARKET, DPE
from database import (
    get_all_properties,
    save_analysis,
    get_session_count,
    get_first_session_date,
)


# ─── Rule-Based Metrics ───────────────────────────────────────────────────────

def _calc_metrics(prop: dict) -> dict:
    """Calculate investment score and financial metrics for one property."""
    arrond = prop.get("arrondissement", "")
    market = LYON_MARKET.get(arrond, {"avg_price_m2": 4300, "rental_yield_pct": 4.5})
    dpe_key = prop.get("dpe", "D") or "D"
    dpe_info = DPE.get(dpe_key, DPE["D"])

    price = prop.get("price", 0) or 0
    size = prop.get("size", 1) or 1
    price_m2 = price / size
    market_avg = market["avg_price_m2"]

    # ── Price vs. market ───────────────────────────────────────
    price_ratio = price_m2 / market_avg if market_avg else 1.0
    price_vs_market_pct = (price_ratio - 1) * 100

    # ── Rental yield ───────────────────────────────────────────
    rental_yield = market["rental_yield_pct"] / 100
    annual_rent = price * rental_yield
    monthly_rent = annual_rent / 12

    # ── Renovation economics ───────────────────────────────────
    reno_cost = dpe_info["reno_cost_m2"] * size
    total_investment = price + reno_cost
    # Post-renovation market value (assume upgrade to B level)
    post_reno_value = market_avg * DPE["B"]["value_factor"] * size

    # ── 5-year ROI ─────────────────────────────────────────────
    annual_net_rent = annual_rent - dpe_info["energy_cost_yr"]
    total_rent_5yr = annual_net_rent * 5
    capital_gain = post_reno_value - total_investment
    roi_5yr = (
        ((total_rent_5yr + capital_gain) / total_investment) * 100
        if total_investment
        else 0
    )

    # ── Investment score (1-10) ────────────────────────────────
    score = 5.0
    # Under / over priced vs. market
    if price_vs_market_pct < -15:
        score += 2.5
    elif price_vs_market_pct < -5:
        score += 1.5
    elif price_vs_market_pct > 15:
        score -= 2.0
    elif price_vs_market_pct > 5:
        score -= 1.0
    # Renovation upside
    if dpe_key in ("E", "F", "G") and capital_gain > 0:
        score += 1.5
    # Already efficient
    if dpe_key in ("A", "B"):
        score += 0.5
    # High yield area
    if rental_yield > 0.05:
        score += 0.5
    # Strong projected returns
    if roi_5yr > 30:
        score += 1.0
    elif roi_5yr < 0:
        score -= 1.0

    score = max(1.0, min(10.0, round(score, 1)))

    is_undervalued = price_vs_market_pct < -8 or (
        dpe_key in ("E", "F", "G")
        and price_vs_market_pct < 0
        and capital_gain > price * 0.10
    )

    return {
        "score": score,
        "price_m2": round(price_m2),
        "market_avg_m2": market_avg,
        "price_vs_market_pct": round(price_vs_market_pct, 1),
        "monthly_rent": round(monthly_rent),
        "annual_rent": round(annual_rent),
        "rental_yield_pct": round(rental_yield * 100, 1),
        "reno_cost": round(reno_cost),
        "post_reno_value": round(post_reno_value),
        "capital_gain": round(capital_gain),
        "roi_5yr": round(roi_5yr, 1),
        "is_undervalued": is_undervalued,
        "total_investment": round(total_investment),
    }


# ─── Gemini AI Insight ─────────────────────────────────────────────────────────

def _gemini_insight(prop: dict, metrics: dict) -> str | None:
    """Request a short AI investment verdict via Google Gemini."""
    if not GEMINI_API_KEY:
        return None
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        dpe_label = DPE.get(prop.get("dpe", "D"), {}).get("label", "Unknown")
        prompt = (
            "You are a French real estate investment analyst for Lyon.\n"
            "Give a concise verdict (max 100 words) for this property:\n\n"
            f"- Title: {prop.get('title')}\n"
            f"- Location: {prop.get('arrondissement')}\n"
            f"- Price: EUR {prop.get('price', 0):,}\n"
            f"- Size: {prop.get('size')} m2  |  EUR {metrics['price_m2']:,}/m2\n"
            f"- Market avg: EUR {metrics['market_avg_m2']:,}/m2 "
            f"({metrics['price_vs_market_pct']:+.1f}%)\n"
            f"- DPE: {prop.get('dpe')} ({dpe_label})\n"
            f"- Rental yield: {metrics['rental_yield_pct']}%\n"
            f"- 5yr ROI (incl. renovation): {metrics['roi_5yr']:.1f}%\n"
            f"- Renovation cost: EUR {metrics['reno_cost']:,}\n\n"
            "Include: BUY/HOLD/AVOID, key risk, and one actionable tip."
        )

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            return "(AI skipped: Gemini quota exceeded - try later or upgrade plan)"
        return f"(AI unavailable: {msg[:120]})"


# ─── Report Builder ────────────────────────────────────────────────────────────

def _build_report(properties: list, all_metrics: list) -> str:
    """Compose the full investment report."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    sessions = get_session_count()
    first_date = get_first_session_date()
    first_str = first_date[:10] if first_date else now[:10]

    W = 66  # line width
    lines: list[str] = []

    # Header
    lines.append("=" * W)
    lines.append("    NEX-LYON REAL ESTATE INVESTMENT REPORT".center(W))
    lines.append(f"    Generated: {now}".center(W))
    lines.append("=" * W)

    total = len(properties)
    if total == 0:
        lines.append("\n  No properties to analyze.\n")
        return "\n".join(lines)

    avg_price = sum(p["price"] for p in properties) / total
    avg_size = sum(p.get("size", 0) or 0 for p in properties) / total
    avg_m2 = sum(m["price_m2"] for m in all_metrics) / total

    # ── Market Overview ────────────────────────────────────────
    lines.append("")
    lines.append("  MARKET OVERVIEW")
    lines.append("-" * W)
    lines.append(f"  Properties Analyzed  : {total}")
    lines.append(f"  Database Sessions    : {sessions} (tracking since {first_str})")
    lines.append(f"  Average Price        : EUR {avg_price:,.0f}")
    lines.append(f"  Average Size         : {avg_size:.0f} m2")
    lines.append(f"  Average Price/m2     : EUR {avg_m2:,.0f}")

    # ── Arrondissement Breakdown ───────────────────────────────
    lines.append("")
    lines.append("  BY ARRONDISSEMENT")
    lines.append("-" * W)
    hdr = f"  {'Area':<14} {'#':>3} {'Avg EUR/m2':>12} {'vs Market':>11} {'Yield':>7}"
    lines.append(hdr)
    lines.append(f"  {'---':<14} {'--':>3} {'----------':>12} {'---------':>11} {'-----':>7}")

    arrond_groups: dict[str, list] = {}
    for p, m in zip(properties, all_metrics):
        a = p.get("arrondissement", "?")
        arrond_groups.setdefault(a, []).append(m)

    for a in sorted(arrond_groups):
        grp = arrond_groups[a]
        cnt = len(grp)
        avg = sum(m["price_m2"] for m in grp) / cnt
        vs = sum(m["price_vs_market_pct"] for m in grp) / cnt
        yld = sum(m["rental_yield_pct"] for m in grp) / cnt
        sign = "+" if vs >= 0 else ""
        lines.append(
            f"  {a:<14} {cnt:>3} {f'EUR {avg:,.0f}':>12} "
            f"{f'{sign}{vs:.1f}%':>11} {f'{yld:.1f}%':>7}"
        )

    # ── Property Ranking ───────────────────────────────────────
    ranked = sorted(
        zip(properties, all_metrics), key=lambda x: x[1]["score"], reverse=True
    )

    lines.append("")
    lines.append("  ALL PROPERTIES (ranked by score)")
    lines.append("-" * W)
    lines.append(
        f"  {'#':>2} {'Score':>5}  {'Title':<30} {'EUR/m2':>8} {'DPE':>4} {'5yr ROI':>8}"
    )
    lines.append(
        f"  {'--':>2} {'-----':>5}  {'-----':<30} {'------':>8} {'---':>4} {'-------':>8}"
    )
    for i, (p, m) in enumerate(ranked, 1):
        title = (p.get("title") or "")[:28]
        flag = " *" if m["is_undervalued"] else "  "
        lines.append(
            f"  {i:>2} {m['score']:>5.1f}  {title:<30} "
            f"{m['price_m2']:>7,} {p.get('dpe', '?'):>4} "
            f"{m['roi_5yr']:>7.1f}%{flag}"
        )
    lines.append("  (* = undervalued)")

    # ── Top Undervalued ────────────────────────────────────────
    undervalued = [(p, m) for p, m in ranked if m["is_undervalued"]]
    lines.append("")
    lines.append(f"  TOP UNDERVALUED PROPERTIES ({len(undervalued)} found)")
    lines.append("-" * W)

    if not undervalued:
        lines.append("  No significantly undervalued properties detected.")
    else:
        for i, (p, m) in enumerate(undervalued[:5], 1):
            lines.append("")
            lines.append(f"  {i}. [SCORE {m['score']}/10] {p.get('title', '')}")
            lines.append(
                f"     Price: EUR {p.get('price', 0):,}  |  {p.get('size', 0)} m2  |  "
                f"EUR {m['price_m2']:,}/m2  |  DPE: {p.get('dpe', '?')}"
            )
            lines.append(
                f"     {m['price_vs_market_pct']:+.1f}% vs market avg "
                f"(EUR {m['market_avg_m2']:,}/m2) for {p.get('arrondissement', '')}"
            )
            lines.append(
                f"     Est. Rent: EUR {m['monthly_rent']:,}/mo  |  "
                f"Yield: {m['rental_yield_pct']}%  |  5yr ROI: {m['roi_5yr']:.1f}%"
            )
            if m["reno_cost"] > 0:
                lines.append(
                    f"     Renovation: EUR {m['reno_cost']:,} -> "
                    f"Post-reno value: EUR {m['post_reno_value']:,} "
                    f"(gain: EUR {m['capital_gain']:,})"
                )
            if m.get("ai_insight"):
                # Wrap long AI text
                insight = m["ai_insight"].replace("\n", " ")
                lines.append(f"     AI: {insight}")

    # ── Footer ─────────────────────────────────────────────────
    lines.append("")
    lines.append("=" * W)
    lines.append("  Disclaimer: Estimates only. Consult a licensed advisor.")
    lines.append("=" * W)

    return "\n".join(lines)


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def analyze() -> tuple[str, list[dict], list[dict]]:
    """Run full analysis pipeline. Returns (report_text, properties, metrics)."""
    properties = get_all_properties()
    if not properties:
        return "  No properties in database. Run the scraper first.", [], []

    print(f"  Analyzing {len(properties)} properties...")

    # 1) Rule-based metrics for every property
    all_metrics = [_calc_metrics(p) for p in properties]

    # 2) AI insights for top undervalued only (saves API calls / cost)
    uv_indices = [i for i, m in enumerate(all_metrics) if m["is_undervalued"]]
    uv_indices.sort(key=lambda i: all_metrics[i]["score"], reverse=True)

    if GEMINI_API_KEY and uv_indices:
        n = min(5, len(uv_indices))
        print(f"  Requesting Gemini AI insights for top {n} opportunities...")
        for idx in uv_indices[:n]:
            insight = _gemini_insight(properties[idx], all_metrics[idx])
            if insight:
                all_metrics[idx]["ai_insight"] = insight
            time.sleep(1)  # polite rate-limiting

    # 3) Persist analyses
    for p, m in zip(properties, all_metrics):
        save_analysis(p["id"], {
            "score": m["score"],
            "roi_5yr": m["roi_5yr"],
            "is_undervalued": m["is_undervalued"],
            "summary": m.get("ai_insight", ""),
        })

    # 4) Build report
    report = _build_report(properties, all_metrics)
    return report, properties, all_metrics

"""
Nex-Lyon Real Estate Analyzer - Web Server
Flask API backend for the React dashboard.
"""

import os
import sys
import datetime
import threading

# Fix encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from flask import Flask, jsonify, send_file, send_from_directory
from config import GOOGLE_SHEET_ID, LYON_MARKET
from database import create_db, get_all_properties
from scraper import scrape
from analyzer import analyze
from sheets import sync_to_sheets

# ─── Flask App ─────────────────────────────────────────────────────────────────

DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")

# ─── Pipeline State (thread-safe via GIL for simple dict ops) ──────────────────

state = {
    "status": "idle",   # idle | running | done | error
    "step": 0,
    "step_label": "",
    "error": None,
}

result_cache = {}


def _run_pipeline():
    """Execute the full scraping + analysis pipeline in a background thread."""
    global state, result_cache
    try:
        # Step 1
        state.update({"status": "running", "step": 1, "step_label": "Setting up database..."})
        create_db()

        # Step 2
        state.update({"step": 2, "step_label": "Scraping property data..."})
        new_count = scrape()

        # Step 3
        state.update({"step": 3, "step_label": "Analyzing investments..."})
        report, properties, metrics = analyze()

        # Step 4
        state.update({"step": 4, "step_label": "Syncing to Google Sheets..."})
        sync_to_sheets(properties, metrics)

        # Save report file
        filename = f"report_{datetime.date.today()}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)

        # ── Build response data ────────────────────────────────────
        sheets_url = (
            f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
            if GOOGLE_SHEET_ID else ""
        )

        # Combine properties + metrics into single list
        combined = []
        for p, m in zip(properties, metrics):
            combined.append({**p, **m})
        combined.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Arrondissement summary
        arrond_map = {}
        for item in combined:
            a = item.get("arrondissement", "?")
            if a not in arrond_map:
                arrond_map[a] = {"prices": [], "vs_market": [], "yields": [], "rois": []}
            arrond_map[a]["prices"].append(item.get("price_m2", 0))
            arrond_map[a]["vs_market"].append(item.get("price_vs_market_pct", 0))
            arrond_map[a]["yields"].append(item.get("rental_yield_pct", 0))
            arrond_map[a]["rois"].append(item.get("roi_5yr", 0))

        arrondissements = []
        for a in sorted(arrond_map):
            d = arrond_map[a]
            cnt = len(d["prices"])
            market = LYON_MARKET.get(a, {})
            arrondissements.append({
                "name": a,
                "count": cnt,
                "avg_m2": round(sum(d["prices"]) / cnt),
                "market_avg": market.get("avg_price_m2", 4300),
                "vs_market": round(sum(d["vs_market"]) / cnt, 1),
                "yield_pct": round(sum(d["yields"]) / cnt, 1),
                "avg_roi": round(sum(d["rois"]) / cnt, 1),
            })

        total = len(combined)
        summary = {
            "total": total,
            "new_count": new_count,
            "avg_price": round(sum(c.get("price", 0) for c in combined) / total) if total else 0,
            "avg_size": round(sum(c.get("size", 0) or 0 for c in combined) / total) if total else 0,
            "avg_m2": round(sum(c.get("price_m2", 0) for c in combined) / total) if total else 0,
            "undervalued": sum(1 for c in combined if c.get("is_undervalued")),
            "best_roi": round(max((c.get("roi_5yr", 0) for c in combined), default=0), 1),
        }

        result_cache = {
            "properties": combined,
            "arrondissements": arrondissements,
            "summary": summary,
            "sheets_url": sheets_url,
            "report_file": filename,
        }

        state.update({"status": "done", "step_label": "Complete!"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        state.update({"status": "error", "error": str(e)})


# ─── API Routes ────────────────────────────────────────────────────────────────

@app.route("/api/run", methods=["POST"])
def api_run():
    if state["status"] == "running":
        return jsonify({"error": "Pipeline already running"}), 409
    state.update({"status": "idle", "step": 0, "step_label": "", "error": None})
    t = threading.Thread(target=_run_pipeline, daemon=True)
    t.start()
    return jsonify({"message": "Pipeline started"})


@app.route("/api/status")
def api_status():
    return jsonify(state)


@app.route("/api/data")
def api_data():
    if not result_cache:
        return jsonify({"error": "No data available"}), 400
    return jsonify({
        "properties": result_cache.get("properties", []),
        "arrondissements": result_cache.get("arrondissements", []),
        "summary": result_cache.get("summary", {}),
        "sheets_url": result_cache.get("sheets_url", ""),
    })


@app.route("/api/report/download")
def api_download():
    fname = result_cache.get("report_file", "")
    if fname and os.path.exists(fname):
        return send_file(
            os.path.abspath(fname),
            as_attachment=True,
            download_name=os.path.basename(fname),
        )
    return jsonify({"error": "No report available"}), 404


@app.route("/api/reset", methods=["POST"])
def api_reset():
    global state, result_cache
    state = {"status": "idle", "step": 0, "step_label": "", "error": None}
    result_cache = {}
    return jsonify({"message": "Reset"})


# ─── Serve Frontend ───────────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    if os.path.exists(os.path.join(DIST_DIR, "index.html")):
        return send_from_directory(DIST_DIR, "index.html")
    return (
        "<h1>Frontend not built</h1>"
        "<p>Run: <code>cd frontend && npm install && npm run build</code></p>"
    ), 200


@app.route("/<path:path>")
def serve_static(path):
    file_path = os.path.join(DIST_DIR, path)
    if os.path.exists(file_path):
        return send_from_directory(DIST_DIR, path)
    return serve_index()


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║  Nex-Lyon Real Estate Analyzer - Web Server  ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    if os.path.exists(os.path.join(DIST_DIR, "index.html")):
        print(f"  Frontend: OK (serving from frontend/dist)")
    else:
        print("  Frontend: NOT BUILT")
        print("  Run: cd frontend && npm install && npm run build")
    print()
    print("  Open: http://localhost:5000")
    print()
    app.run(host="0.0.0.0", port=5000, debug=False)

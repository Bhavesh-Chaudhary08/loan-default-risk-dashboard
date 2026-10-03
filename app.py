"""
Loan Default Risk Memorandum — Flask application
=================================================
Serves the 4-page credit-risk dashboard plus a small JSON API:

    GET /              -> Overview page
    GET /borrower      -> Borrower Analytics page
    GET /loans         -> Loans & Pricing page
    GET /explorer      -> Risk Explorer page
    GET /api/records   -> 39,252 row-level records (client-side filtering)
    GET /api/kpis      -> portfolio KPIs computed in SQL
    GET /health        -> readiness probe

Run:  python app.py   ->   http://localhost:5000
"""

import json
import os
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, render_template

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "loans.db"

app = Flask(__name__)

# Gzip responses: /api/records is ~10 MB raw; compressed it is ~1 MB, which
# keeps hosted free-tier responses well under proxy limits and loads fast.
# flask-compress is in requirements.txt (Docker/PaaS installs get gzip);
# hosts that run system Python without it serve plain responses instead.
try:
    from flask_compress import Compress

    Compress(app)
except ImportError:
    pass


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------
def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
PAGES = {
    "index":    {"template": "index.html",    "section": "§1", "title": "Portfolio Overview",   "page_id": "overview"},
    "borrower": {"template": "borrower.html", "section": "§2", "title": "The Borrower",        "page_id": "borrower"},
    "loans":    {"template": "loans.html",    "section": "§3", "title": "Product &amp; Pricing", "page_id": "loans"},
    "explorer": {"template": "explorer.html", "section": "§4", "title": "Segment Workbench",   "page_id": "explorer"},
}


@app.route("/")
def index():
    return page("index")


@app.route("/borrower")
def borrower():
    return page("borrower")


@app.route("/loans")
def loans():
    return page("loans")


@app.route("/explorer")
def explorer():
    return page("explorer")


def page(key):
    p = PAGES[key]
    return render_template(p["template"], section=p["section"], title=p["title"], page_id=p["page_id"])


# --------------------------------------------------------------------------
# JSON API
# --------------------------------------------------------------------------
@app.route("/api/records")
def api_records():
    """All 39,252 row-level records as one compact JSON document."""
    db = get_db()
    rows = db.execute("SELECT * FROM loans")
    payload = json.dumps([record_dict(r) for r in rows], separators=(",", ":"))
    return app.response_class(payload, mimetype="application/json")


def record_dict(r):
    """DB row -> the compact dict the dashboard's JS engine expects."""
    return {
        "amt":    r["loan_amnt"],
        "rate":   r["int_rate"],
        "dti":    r["dti"],
        "fico":   r["fico"],
        "inc":    r["annual_inc"],
        "home":   r["home_ownership"],
        "verif":  r["verification_status"],
        "purpose": r["purpose"],
        "term":   r["term"],
        "def":    r["is_default"],
        "ficoB":  r["fico_band"],
        "dtiB":   r["dti_band"],
        "incB":   r["income_band"],
        "rateB":  r["int_rate_band"],
        "empB":   r["emp_length_band"],
        "loss":   r["est_loss_at_default"],
    }


@app.route("/api/kpis")
def api_kpis():
    """Portfolio KPIs computed by SQL (mirror of queries/analysis_queries.sql Q0)."""
    db = get_db()
    row = db.execute(
        """
        SELECT COUNT(*)                        AS n,
               SUM(is_default)                 AS defaults,
               SUM(loan_amnt)                  AS volume,
               SUM(est_loss_at_default)        AS loss,
               AVG(int_rate)                   AS avg_rate,
               AVG(fico)                       AS avg_fico,
               AVG(dti)                        AS avg_dti,
               AVG(annual_inc)                 AS avg_inc,
               100.0 * SUM(is_default) / COUNT(*) AS default_rate
        FROM loans
        """
    ).fetchone()
    return jsonify(dict(row))


@app.route("/api/sql")
def api_sql():
    """Serve the documented SQL analysis file (13 queries, Q0–Q12)."""
    from flask import Response
    sql = (BASE_DIR / "queries" / "analysis_queries.sql").read_text(encoding="utf-8")
    return Response(sql, mimetype="text/plain")


@app.route("/health")
def health():
    db = get_db()
    n = db.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
    return jsonify(status="ok", loans=n)


if __name__ == "__main__":
    # Hosted (Render / Railway / etc.): the platform injects PORT -> serve on
    # 0.0.0.0 with the debugger off.  Local: python app.py -> http://localhost:5000
    _port = int(os.environ.get("PORT") or 0)
    if _port > 0:
        app.run(host="0.0.0.0", port=_port, debug=False)
    else:
        app.run(host="127.0.0.1", port=5000, debug=True)

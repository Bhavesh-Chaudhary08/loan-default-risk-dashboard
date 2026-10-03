# Run the Loan Default Risk Memorandum (Flask)

## VS Code (one click)

1. Open the project folder in VS Code (`D:\data analyst 1`).
2. Press **Ctrl + Shift + B**.
3. The Flask server starts and your browser opens the dashboard automatically.

To stop: click the terminal, press **Ctrl + C**.

(If Ctrl+Shift+B is taken by another extension, use **Terminal → Run Task → Start Dashboard & Open Browser**.)

## Manual (any terminal)

```bash
cd "D:\data analyst 1"
pip install -r requirements.txt   # first time only
python app.py
```

Then open: http://localhost:5000

## What the Flask app serves

| Route | Purpose |
|---|---|
| `/` `/borrower` `/loans` `/explorer` | The four memorandum pages |
| `/api/records` | 39,252 row-level records streamed as JSON (from SQLite) |
| `/api/kpis` | Portfolio KPIs computed in SQL |
| `/health` | Readiness probe (`{"status": "ok", "loans": 39252}`) |

```
app.py                  # Flask app: pages + JSON API
templates/              # base.html + 4 pages (Jinja2)
static/                 # style.css, app.js, queries/
data/loans.db           # SQLite database the API reads
```

## Rebuild data (optional)

```bash
python scripts/build_data.py
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: flask` | `pip install -r requirements.txt` |
| Browser says `ERR_CONNECTION_REFUSED` | The server hadn't finished starting (or failed). Look at the **Run Dashboard (server only)** terminal: wait for the line `Running on http://127.0.0.1:5000`, then refresh the browser. If that terminal shows an error instead, fix it before retrying. |
| Port busy | `python app.py` uses 5000; edit the port in the last line of `app.py` |
| Empty charts | Check http://localhost:5000/health returns `status: ok` |

---
title: Loan Default Risk Dashboard
emoji: 💳
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# 💳 Loan Default Risk Dashboard — BFSI Analytics

[![Live demo](https://img.shields.io/badge/live-demo-7a1f2b?style=flat-square)](https://bhaveshcdhry.pythonanywhere.com)

**▶ Live dashboard: [bhaveshcdhry.pythonanywhere.com](https://bhaveshcdhry.pythonanywhere.com)**
— always on, free-hosted on PythonAnywhere (Flask + SQLite + Docker-ready).

End-to-end data analytics project in the **BFSI (Banking & Financial Services)** domain:
a credit-risk analysis of a real peer-to-peer lending portfolio, with an interactive
executive dashboard.

Inspired by **Project 1 — "Loan Default Risk Dashboard"** from
[*15 Data Analyst Project Ideas That Get You Hired at Top MNCs*](https://www.youtube.com/watch?v=dInlnsslGm4)
(Mansi G). The video's recipe: a real dataset + the right tools + the exact business
question that makes it recruiter-ready.

---

## 🧰 Stack

| Layer | Tool |
|---|---|
| Data processing | Python 3, pandas, NumPy |
| Backend | **Flask** (Python) — page routing + JSON API over SQLite |
| Database / SQL | SQLite (`data/loans.db`, 39,252-row `loans` table) |
| Visualisation | Multi-page interactive BI app — Jinja2 templates + Chart.js (+ matrix plugin) |
| Reproducibility | One command rebuilds DB + dashboard data: `python scripts/build_data.py` |

## 📊 Dataset

**LendingClub consumer loans, 2007–2011** — the exact dataset referenced in the video
(Kaggle *LendingClub Loan Dataset*, here a pre-cleaned derivative with 39,252
fully-paid/defaulted records and 41 columns).

- `data/loans_2007.csv` — raw input (one-hot encoded categories)
- Borrower profile: FICO, DTI, income, employment length, home ownership
- Loan profile: amount, term, interest rate, purpose, verification status
- Outcome: fully paid vs defaulted

## ❓ Business Questions Answered

1. **How big is the book and how much is leaking?** → KPI strip (volume, default rate, estimated loss)
2. **Does the credit-score risk ladder hold?** → default rate by FICO band
3. **Is risk actually priced in?** → default rate vs interest-rate band
4. **Where do the dollars leak?** → default % and estimated $ loss by loan purpose
5. **Does debt burden stack on top of credit score?** → FICO × DTI risk heat map
6. **Do higher earners and homeowners default less?** → income / home-ownership cuts
7. **Is "verified income" safer?** → the verification paradox (no — selection effect)
8. **Where should credit policy tighten first?** → ranked top-loss segment table (filterable)

## 🖥️ A 4-Page Interactive BI App (not just a dashboard)

The dashboard is a small application with **shared global filters that persist across
pages** (via URL params) and **click-to-filter / click-to-drill on every chart**:

| Page | What's on it | Interactivity |
|---|---|---|
| **Overview** | KPI strip, FICO risk ladder + pricing overlay, purpose $-loss, rate bands, FICO×DTI matrix, term/amount exposure | Click any bar → **drill panel** with segment KPIs, mix and a mini FICO chart; click bars on filter dimensions → **cross-filters everything** |
| **Borrower Analytics** | Income/DTI/employment cuts, home-ownership, FICO×income bubble map, verification paradox | Same click-drill + cross-filter; **FICO & DTI sliders** reshape everything live |
| **Loans & Pricing** | Rate-band risk, term split, amount buckets, risk-vs-return scatter, pricing adequacy | Charts cross-filter; KPI strip recomputes loan-level math from the selection |
| **Risk Explorer** | FICO×DTI matrix, FICO distribution, **credit-committee segment workbench** | **Sortable table** (click headers), preset segment filters (Default > 20%, Loss > $5M, ≥2,000 loans), cell click → drill |

**Global filter bar** (all pages): home ownership, verification, purpose, term,
income band selects + **FICO min / DTI max sliders**, a live "loans in scope" counter,
one-click reset, and toasts on every action.

## 📈 Headline Findings

- **14.43% portfolio default rate** (5,666 of 39,252 loans) → **~$58.5M estimated loss**
  at 85% severity on defaulted principal.
- **Credit score is the dominant risk driver**: 740+ FICO defaults at **8.6%** vs
  **19.2%** for 660–699 — a **2.2× gap** across adjacent bands, while average pricing
  moves only ~6 points. Marginal loans in the worst band are mispriced.
- **Risk-based pricing broadly works**: <8% loans default at 5.4% vs **27.8%** for
  16%+ loans (~5× step-up), consistent with rates tracking risk.
- **Small business loans are the loss engine**: 26.5% default rate and the largest
  dollar leak (~$5.9M) despite fewer loans — classic SME risk concentration.
- **60-month terms default ~2.3× more** than 36-month (22.5% vs 11.1%).
- **The verification paradox**: "Verified" income loans default *more* (16.5%) than
  "Not Verified" (12.7%) — verification is triggered for riskier applicants
  (a selection effect, not causation). Great interview talking point.
- **Risk compounds**: the worst FICO×DTI cell (660–699 + DTI 20–29) defaults at
  20.5%; the same FICO with low DTI defaults at 18.2%, and excellent-FICO/low-DTI
  at 8.1% — policy tightening should target the 2-D cell, not one factor.

## 🚀 Run It (Flask)

```bash
# 1. Install dependencies (Flask, pandas, numpy)
pip install -r requirements.txt

# 2. Rebuild database + dashboard data (optional — outputs are committed)
python scripts/build_data.py

# 3. Start the Flask app
python app.py
# → open http://localhost:5000

# 4. Run any SQL analysis directly
sqlite3 data/loans.db < queries/analysis_queries.sql
```

### Flask routes

| Route | Purpose |
|---|---|
| `/` · `/borrower` · `/loans` · `/explorer` | The four memorandum pages (Jinja2 templates) |
| `/api/records` | 39,252 row-level records as JSON — read from SQLite on request |
| `/api/kpis` | Portfolio KPIs computed in SQL |
| `/health` | Readiness probe |

> The SQL analyses are also downloadable from the running app at `/api/sql`.

## 📁 Project Structure

```
├── app.py                  # Flask application (pages + JSON API)
├── templates/              # Jinja2: base.html + the 4 pages
├── static/                 # style.css, app.js (engine), queries/
├── data/
│   ├── loans_2007.csv      # raw LendingClub data (39,252 loans)
│   ├── loans.db            # SQLite database (loans table + indexes)
│   └── loans_2007.csv      # raw LendingClub input
├── scripts/
│   └── build_data.py       # ETL: clean → engineer features → SQLite
├── queries/
│   └── analysis_queries.sql# 13 documented SQL analyses (Q0–Q12)
└── README.md
```

## 🗃️ Data Model (loans table)

Key columns: `loan_amnt`, `int_rate`, `installment`, `emp_length`, `annual_inc`,
`dti`, `fico`, `revol_util`, `home_ownership`, `verification_status`, `purpose`,
`term`, `is_default` (0/1), plus derived bands `fico_band`, `dti_band`,
`income_band`, `int_rate_band` and `est_loss_at_default` (= amount × 85% when defaulted).

## 💼 Resume Bullets (copy-paste)

- Built an end-to-end loan-default risk analysis on **39K real LendingClub loans**
  ($437M volume): **Flask + pandas ETL → SQLite → JSON API → 4-page interactive BI app**
  with global cross-filters, click-to-drill on every chart and a sortable segment workbench.
- Wrote **13 documented SQL analyses** quantifying default drivers across FICO, DTI,
  income, term and purpose; identified a **2.2× default-rate gap** between adjacent
  credit bands with inadequate rate compensation.
- Surfaced the **income-verification paradox** (verified loans default 16.5% vs 12.7%)
  and a **FICO×DTI risk matrix** pinpointing where credit policy should tighten,
  quantifying **~$58.5M estimated loss** at 85% severity.

## 🎤 Interview Talking Points

1. **Why 85% severity?** Conservative industry rule-of-thumb for unsecured consumer
   loans: charge-off minus modest post-default recoveries. State the assumption —
   interviewers care that you *have* one.
2. **Correlation ≠ causation** — the verification paradox is a selection effect:
   lenders verify income *because* the applicant looks risky. Same trap as
   "customers who call support churn more".
3. **Why HAVING COUNT(*) > 500?** Small segments produce unstable default rates;
   filtering avoids noisy rankings.
4. **Next step I'd take:** replace banding with a logistic-regression / gradient-
   boosting PD model, validate with AUC + KS statistic, and rank segments by
   *expected loss* (PD × LGD × EAD) instead of default rate alone.

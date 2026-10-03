"""
Loan Default Risk Dashboard — Data Pipeline
===========================================
Project 1 of "15 Data Analyst Project Ideas That Get You Hired at Top MNCs"
(Mansi G, YouTube) — BFSI domain: Loan Default Risk Analysis.

Dataset : LendingClub 2007 loans (Kaggle "LendingClub Loan Dataset" derivative,
          39,252 real loan records, pre-cleaned one-hot encoded).
Tools   : Python (pandas) + SQLite + Chart.js dashboard.

This script:
  1. Loads the raw CSV and un-dummies the one-hot columns back to readable
     categories (home_ownership, verification_status, purpose, term).
  2. Maps loan_status -> 1 (defaulted) / 0 (fully paid). This is the target
     business flag for the whole dashboard.
  3. Derives analyst features: FICO bands, income bands, DTI bands,
     interest-rate bands, estimated loss at default.
  4. Writes a tidy SQLite database (loans.db) so every dashboard chart is also
     reproducible with plain SQL (queries/analysis_queries.sql).
  5. Prints the full SQL result set for review (queries/analysis_queries.sql).
"""

import sqlite3

import pandas as pd
import numpy as np

RAW_CSV = "data/loans_2007.csv"
DB_PATH = "data/loans.db"

# ---------------------------------------------------------------------------
# 1. Load + reshape
# ---------------------------------------------------------------------------
df = pd.read_csv(RAW_CSV)
print(f"Loaded {len(df):,} loan records, {df.shape[1]} raw columns")

# Un-one-hot: pick the dummy column with 1, map to a clean label
HOME_MAP = {
    "home_ownership_MORTGAGE": "MORTGAGE", "home_ownership_OWN": "OWN",
    "home_ownership_RENT": "RENT", "home_ownership_NONE": "NONE",
    "home_ownership_OTHER": "OTHER",
}
VERIF_MAP = {
    "verification_status_Not Verified": "Not Verified",
    "verification_status_Source Verified": "Source Verified",
    "verification_status_Verified": "Verified",
}
PURPOSE_MAP = {c: c.replace("purpose_", "").replace("_", " ") for c in df.columns if c.startswith("purpose_")}

df["home_ownership"] = df[list(HOME_MAP)].idxmax(axis=1).map(HOME_MAP)
df["verification_status"] = df[list(VERIF_MAP)].idxmax(axis=1).map(VERIF_MAP)
df["purpose"] = df[list(PURPOSE_MAP)].idxmax(axis=1).map(PURPOSE_MAP)
df["term"] = np.where(df["term_ 36 months"] == 1, "36 months", "60 months")

# ---------------------------------------------------------------------------
# 2. Target flag: loan_status (already binary in this file:
#    1 = Fully Paid, 0 = Defaulted/Charged Off) — make it explicit + readable.
#    NOTE: in the original Kaggle CSV this column is text ("Fully Paid",
#    "Charged Off"); this derivative encodes it 1/0. If you download the raw
#    Kaggle file, map: Charged Off/Default -> 1, Fully Paid -> 0.
# ---------------------------------------------------------------------------
PAYOFF_CODE = 1  # value in loan_status meaning the loan was fully paid
DEFAULT_CODE = 0
df["is_default"] = (df["loan_status"].astype(int) == DEFAULT_CODE).astype(int)
df["status_label"] = df["is_default"].map({1: "Defaulted", 0: "Fully Paid"})

# ---------------------------------------------------------------------------
# 3. Derived analyst features
# ---------------------------------------------------------------------------
df["fico"] = df["fico_range_high"].astype(float)
df["loan_amnt"] = df["loan_amnt"].astype(float)
df["annual_inc"] = df["annual_inc"].astype(float)
df["dti"] = df["dti"].astype(float)

def band(series, edges, labels):
    """pd.cut with right=False; edges must be len(labels)+1."""
    assert len(edges) == len(labels) + 1, f"{len(edges)} edges vs {len(labels)} labels"
    return pd.cut(series, bins=edges, labels=labels, right=False).astype(str)

# NOTE: this LendingClub cut has no FICO < 660 loans (LC's floor at the time
# was 660), so the ladder starts at 'Good'. Bands kept for parity with the
# standard 5-tier scale used in credit-risk reporting.
df["fico_band"] = band(df["fico"],
                       [0, 620, 660, 700, 740, 900],
                       ["<620 Poor", "620-659 Fair", "660-699 Good",
                        "700-739 Very Good", "740+ Excellent"])

df["dti_band"] = band(df["dti"],
                      [-1, 10, 20, 30, 1000],
                      ["0-9 Low", "10-19 Moderate", "20-29 High", "30+ Very High"])

df["income_band"] = band(df["annual_inc"],
                         [0, 40000, 70000, 100000, 150000, 10_000_000],
                         ["<40k", "40-70k", "70-100k", "100-150k", "150k+"])

df["int_rate_band"] = band(df["int_rate"].astype(float),
                           [0, 8, 12, 16, 100],
                           ["<8%", "8-12%", "12-16%", "16%+"])

df["emp_length_band"] = df["emp_length"].apply(
    lambda x: "<1 yr" if x == 0 else ("10+ yrs" if x == 10 else f"{int(x)} yrs"))

# Exposure analytics: realised-loss assumption a risk team would apply
# (85% severity on defaulted principal is a standard conservative estimate:
# loan amount minus modest post-chargeoff recoveries)
SEVERITY = 0.85
df["est_loss_at_default"] = np.where(df["is_default"] == 1, df["loan_amnt"] * SEVERITY, 0.0)

n_defaults = int(df["is_default"].sum())
print(f"Default rate overall: {df['is_default'].mean():.1%} ({n_defaults:,} of {len(df):,} loans)")
print(f"Total loan volume: ${df['loan_amnt'].sum():,.0f}")
print(f"Estimated loss from defaults: ${df['est_loss_at_default'].sum():,.0f}")

# ---------------------------------------------------------------------------
# 4. Persist tidy table to SQLite
# ---------------------------------------------------------------------------
keep_cols = [
    "loan_amnt", "int_rate", "installment", "emp_length", "annual_inc",
    "zip_code", "dti", "delinq_2yrs", "fico", "last_fico_range_high",
    "inq_last_6mths", "open_acc", "pub_rec", "revol_bal", "revol_util",
    "total_acc", "home_ownership", "verification_status", "purpose", "term",
    "is_default", "status_label", "fico_band", "dti_band", "income_band",
    "int_rate_band", "emp_length_band", "est_loss_at_default",
]
db_df = df[keep_cols].copy()
db_df = db_df.rename(columns={"last_fico_range_high": "last_fico"})

con = sqlite3.connect(DB_PATH)
db_df.to_sql("loans", con, if_exists="replace", index=False)
con.execute("CREATE INDEX IF NOT EXISTS idx_default ON loans(is_default)")
con.commit()
print(f"Wrote {len(db_df):,} rows to {DB_PATH}")

# ---------------------------------------------------------------------------
# 5b. Row-level export for the interactive multi-page dashboard
#     Compact records so client-side filters (global cross-filtering) stay fast.
# ---------------------------------------------------------------------------
records = df[[
    "loan_amnt", "int_rate", "dti", "fico", "annual_inc",
    "home_ownership", "verification_status", "purpose", "term",
    "is_default", "fico_band", "dti_band", "income_band", "int_rate_band",
    "emp_length_band", "est_loss_at_default",
]].copy()
records.columns = ["amt", "rate", "dti", "fico", "inc",
                   "home", "verif", "purpose", "term",
                   "def", "ficoB", "dtiB", "incB", "rateB", "empB", "loss"]
records["amt"] = records["amt"].round(0)
records["rate"] = records["rate"].round(2)
records["dti"] = records["dti"].round(1)
records["inc"] = records["inc"].round(0)
records["loss"] = records["loss"].round(0)
# NOTE: row-level records are now served straight from loans.db by the Flask API
# (/api/records) — no JSON export needed. The block below only prints a preview.
print(f"Row-level records ready: {len(records):,} rows (served via /api/records)")
print(records.head(3).to_string(index=False))

# ---------------------------------------------------------------------------
# 6. Chart data (all queries mirrored in queries/analysis_queries.sql)
# ---------------------------------------------------------------------------
Q = {
    "kpi": """
        SELECT COUNT(*) AS total_loans,
               SUM(loan_amnt) AS total_volume,
               AVG(int_rate) AS avg_rate,
               AVG(fico) AS avg_fico,
               AVG(dti) AS avg_dti,
               SUM(is_default) AS defaults,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct,
               SUM(est_loss_at_default) AS est_loss
        FROM loans
    """,
    "by_grade": """
        SELECT fico_band AS band, COUNT(*) AS loans, SUM(is_default) AS defaults,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct,
               ROUND(AVG(int_rate), 2) AS avg_int_rate
        FROM loans GROUP BY fico_band
        ORDER BY CASE fico_band
            WHEN '<620 Poor' THEN 1 WHEN '620-659 Fair' THEN 2 WHEN '660-699 Good' THEN 3
            WHEN '700-739 Very Good' THEN 4 ELSE 5 END
    """,
    "by_rate": """
        SELECT int_rate_band AS band, COUNT(*) AS loans,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct
        FROM loans GROUP BY int_rate_band
        ORDER BY CASE int_rate_band
            WHEN '<8%' THEN 1 WHEN '8-12%' THEN 2 WHEN '12-16%' THEN 3 ELSE 4 END
    """,
    "by_purpose": """
        SELECT purpose, COUNT(*) AS loans, SUM(is_default) AS defaults,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct,
               ROUND(SUM(est_loss_at_default) / 1000000.0, 2) AS est_loss_m
        FROM loans GROUP BY purpose
        HAVING COUNT(*) > 500
        ORDER BY default_rate_pct DESC
    """,
    "by_dti": """
        SELECT dti_band AS band, COUNT(*) AS loans,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct
        FROM loans GROUP BY dti_band
        ORDER BY CASE dti_band
            WHEN '0-9 Low' THEN 1 WHEN '10-19 Moderate' THEN 2
            WHEN '20-29 High' THEN 3 ELSE 4 END
    """,
    "by_income": """
        SELECT income_band AS band, COUNT(*) AS loans, SUM(is_default) AS defaults,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct
        FROM loans GROUP BY income_band
        ORDER BY CASE income_band
            WHEN '<40k' THEN 1 WHEN '40-70k' THEN 2 WHEN '70-100k' THEN 3
            WHEN '100-150k' THEN 4 ELSE 5 END
    """,
    "by_home": """
        SELECT home_ownership, COUNT(*) AS loans,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct
        FROM loans GROUP BY home_ownership HAVING COUNT(*) > 200 ORDER BY loans DESC
    """,
    "by_term": """
        SELECT term, COUNT(*) AS loans,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct,
               ROUND(AVG(int_rate), 2) AS avg_int_rate
        FROM loans GROUP BY term
    """,
    "by_verif": """
        SELECT verification_status, COUNT(*) AS loans,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct
        FROM loans GROUP BY verification_status
    """,
    "fico_hist": """
        SELECT (CAST(fico AS INT) / 10) * 10 AS fico_decile, COUNT(*) AS loans
        FROM loans GROUP BY fico_decile ORDER BY fico_decile
    """,
    "amt_hist": """
        SELECT (CAST(loan_amnt AS INT) / 5000) * 5000 AS amt_bucket,
               COUNT(*) AS loans,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct
        FROM loans GROUP BY amt_bucket ORDER BY amt_bucket
    """,
    "risk_matrix": """
        SELECT fico_band, dti_band, COUNT(*) AS loans,
               ROUND(100.0 * SUM(is_default) / COUNT(*), 2) AS default_rate_pct
        FROM loans GROUP BY fico_band, dti_band
    """,
}

for name, sql in Q.items():
    df = pd.read_sql_query(sql, con)
    print(f"\n=== {name} ===")
    print(df.to_string(index=False))
con.close()

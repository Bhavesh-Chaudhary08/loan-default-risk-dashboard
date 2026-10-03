-- ============================================================================
-- Loan Default Risk Dashboard — SQL Analysis Queries
-- ============================================================================
-- Project 1 of "15 Data Analyst Project Ideas That Get You Hired at Top MNCs"
-- BFSI domain | Database: SQLite (data/loans.db) | Table: loans (39,252 rows)
--
-- Business context: A digital-lending risk team wants to understand WHERE
-- defaults concentrate across borrower segments so they can tighten credit
-- policy on the riskiest slices without killing approval volume.
--
-- Each query below feeds one panel of the interactive dashboard
-- (dashboard/index.html). Run any of them with:
--     sqlite3 data/loans.db < queries/analysis_queries.sql
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Q0. HEADLINE KPIs — portfolio snapshot
--     Business question: How big is the book, and how much is leaking to
--     defaults?
-- ----------------------------------------------------------------------------
SELECT
    COUNT(*)                                              AS total_loans,
    ROUND(SUM(loan_amnt) / 1000000.0, 1)                  AS total_volume_musd,
    ROUND(AVG(int_rate), 2)                               AS avg_int_rate_pct,
    ROUND(AVG(fico), 0)                                   AS avg_fico,
    ROUND(AVG(dti), 1)                                    AS avg_dti,
    SUM(is_default)                                       AS defaulted_loans,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct,
    ROUND(SUM(est_loss_at_default) / 1000000.0, 1)        AS est_loss_musd
FROM loans;


-- ----------------------------------------------------------------------------
-- Q1. DEFAULT RATE BY FICO BAND (credit-grade risk curve)
--     Business question: Does the classic risk ladder hold — do lower credit
--     scores default materially more? This is the single most important
--     underwriting signal.
-- ----------------------------------------------------------------------------
SELECT
    fico_band                                             AS band,
    COUNT(*)                                              AS loans,
    SUM(is_default)                                       AS defaults,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct,
    ROUND(AVG(int_rate), 2)                               AS avg_int_rate_pct
FROM loans
GROUP BY fico_band
ORDER BY CASE fico_band
    WHEN '<620 Poor' THEN 1 WHEN '620-659 Fair' THEN 2 WHEN '660-699 Good' THEN 3
    WHEN '700-739 Very Good' THEN 4 ELSE 5 END;


-- ----------------------------------------------------------------------------
-- Q2. DEFAULT RATE BY INTEREST-RATE BAND (is risk priced in?)
--     Business question: Are higher rates compensating for higher risk — or
--     do high-rate loans default even more (a pricing red flag)?
-- ----------------------------------------------------------------------------
SELECT
    int_rate_band                                         AS band,
    COUNT(*)                                              AS loans,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct
FROM loans
GROUP BY int_rate_band
ORDER BY CASE int_rate_band
    WHEN '<8%' THEN 1 WHEN '8-12%' THEN 2 WHEN '12-16%' THEN 3 ELSE 4 END;


-- ----------------------------------------------------------------------------
-- Q3. DEFAULT RATE BY LOAN PURPOSE (loss concentration)
--     Business question: Which loan purposes lose the most money? (Includes
--     estimated loss in $M so risk teams see dollars, not just percentages.)
--     Filtered to purposes with > 500 loans so rates are statistically solid.
-- ----------------------------------------------------------------------------
SELECT
    purpose,
    COUNT(*)                                              AS loans,
    SUM(is_default)                                       AS defaults,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct,
    ROUND(SUM(est_loss_at_default) / 1000000.0, 2)        AS est_loss_musd
FROM loans
GROUP BY purpose
HAVING COUNT(*) > 500
ORDER BY default_rate_pct DESC;


-- ----------------------------------------------------------------------------
-- Q4. DEFAULT RATE BY DTI BAND (debt-burden stress test)
--     Business question: Does a borrower's existing debt load predict
--     default even after controlling for credit score?
-- ----------------------------------------------------------------------------
SELECT
    dti_band                                              AS band,
    COUNT(*)                                              AS loans,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct
FROM loans
GROUP BY dti_band
ORDER BY CASE dti_band
    WHEN '0-9 Low' THEN 1 WHEN '10-19 Moderate' THEN 2
    WHEN '20-29 High' THEN 3 ELSE 4 END;


-- ----------------------------------------------------------------------------
-- Q5. DEFAULT RATE BY INCOME BAND
--     Business question: Do higher earners default less — and where is the
--     cliff?
-- ----------------------------------------------------------------------------
SELECT
    income_band                                           AS band,
    COUNT(*)                                              AS loans,
    SUM(is_default)                                       AS defaults,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct
FROM loans
GROUP BY income_band
ORDER BY CASE income_band
    WHEN '<40k' THEN 1 WHEN '40-70k' THEN 2 WHEN '70-100k' THEN 3
    WHEN '100-150k' THEN 4 ELSE 5 END;


-- ----------------------------------------------------------------------------
-- Q6. DEFAULT RATE BY HOME OWNERSHIP
--     Business question: Is housing stability (own/mortgage vs rent) a real
--     risk differentiator?
-- ----------------------------------------------------------------------------
SELECT
    home_ownership,
    COUNT(*)                                              AS loans,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct
FROM loans
GROUP BY home_ownership
HAVING COUNT(*) > 200
ORDER BY loans DESC;


-- ----------------------------------------------------------------------------
-- Q7. DEFAULT RATE BY TERM (36 vs 60 months)
--     Business question: Do longer loans carry structurally higher risk?
-- ----------------------------------------------------------------------------
SELECT
    term,
    COUNT(*)                                              AS loans,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct,
    ROUND(AVG(int_rate), 2)                               AS avg_int_rate_pct
FROM loans
GROUP BY term;


-- ----------------------------------------------------------------------------
-- Q8. DEFAULT RATE BY INCOME VERIFICATION STATUS
--     Business question: The counterintuitive one — does *verified* income
--     really mean safer loans? (Historically: NO — verification is triggered
--     for riskier applicants, so verified loans default MORE. Great interview
--     talking point about selection effects.)
-- ----------------------------------------------------------------------------
SELECT
    verification_status,
    COUNT(*)                                              AS loans,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct
FROM loans
GROUP BY verification_status;


-- ----------------------------------------------------------------------------
-- Q9. FICO DISTRIBUTION (portfolio composition histogram)
-- ----------------------------------------------------------------------------
SELECT
    (CAST(fico AS INT) / 10) * 10                         AS fico_decile,
    COUNT(*)                                              AS loans
FROM loans
GROUP BY fico_decile
ORDER BY fico_decile;


-- ----------------------------------------------------------------------------
-- Q10. LOAN SIZE BUCKETS + DEFAULT RATE
--     Business question: Do bigger loans default more (exposure concentration)?
-- ----------------------------------------------------------------------------
SELECT
    (CAST(loan_amnt AS INT) / 5000) * 5000                AS amt_bucket,
    COUNT(*)                                              AS loans,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct
FROM loans
GROUP BY amt_bucket
ORDER BY amt_bucket;


-- ----------------------------------------------------------------------------
-- Q11. RISK MATRIX — FICO x DTI (two-dimensional segmentation)
--     Business question: Where do the two worst risk factors stack? This is
--     the heat map panel and the natural "credit policy" output: the red
--     cells are where underwriting should tighten first.
-- ----------------------------------------------------------------------------
SELECT
    fico_band,
    dti_band,
    COUNT(*)                                              AS loans,
    ROUND(100.0 * SUM(is_default) / COUNT(*), 2)          AS default_rate_pct
FROM loans
GROUP BY fico_band, dti_band;


-- ----------------------------------------------------------------------------
-- BONUS Q12. RANKING VIEW — worst combined segments by expected loss
--     The "so what" query for a credit committee: rank risky segments by
--     estimated dollar loss and flag anything above portfolio-average risk.
-- ----------------------------------------------------------------------------
WITH segment AS (
    SELECT
        fico_band,
        dti_band,
        COUNT(*)                                          AS loans,
        SUM(is_default)                                   AS defaults,
        SUM(loan_amnt)                                    AS exposure,
        SUM(est_loss_at_default)                          AS est_loss,
        100.0 * SUM(is_default) / COUNT(*)                AS dr
    FROM loans
    GROUP BY fico_band, dti_band
)
SELECT
    fico_band,
    dti_band,
    loans,
    defaults,
    ROUND(dr, 2)                                          AS default_rate_pct,
    ROUND(exposure / 1000000.0, 2)                        AS exposure_musd,
    ROUND(est_loss / 1000000.0, 2)                        AS est_loss_musd
FROM segment
WHERE loans >= 300
ORDER BY est_loss DESC
LIMIT 10;

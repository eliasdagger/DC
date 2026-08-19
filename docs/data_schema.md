# Data Schema

Every table in `dagher.duckdb`, what it holds, and how the pieces join.

Two conventions run through all of it:

- **`ticker` is the join key.** One company, one sector, stated in one place. Nothing else carries a copy.
- **Dates are load-bearing.** Several tables append rather than overwrite, and reads are filtered by date so historical scoring can't see the future.

---

## Layer 1 — Portfolio Analytics

### `prices`

OHLCV from yfinance, cached so calculations don't re-hit the network.

| Column | Type | |
|---|---|---|
| `ticker` | VARCHAR | |
| `date` | DATE | trading day |
| `open` `high` `low` `close` | FLOAT | |
| `volume` | INTEGER | |

Written by `cache_prices()`, read by `get_cached_price()` and everything in `features/returns.py`.

`get_cached_price` uses `date <= ?` rather than exact match, so a weekend or holiday lookup returns the most recent prior close instead of nothing. That pattern — most-recent-on-or-before — recurs throughout the schema.

**No uniqueness constraint.** Re-running ingestion for a date range already cached will duplicate rows.

### `clients`

| Column | Type | |
|---|---|---|
| `id` | INTEGER | |
| `name` | VARCHAR | |
| `risk_tolerance` | VARCHAR | |
| `age` | INTEGER | |
| `cash_position` | FLOAT | |
| `goals` | VARCHAR | |
| `considerations` | VARCHAR | |

⚠️ The column is `id`, but `Client.client_id` is the model field. The mapping is positional in `add_client()`, so it works — but a `SELECT *` into a model would not.

`Client.holdings` has no column here. Holdings live in their own table and are joined on `client_id`.

### `holdings`

One row per position. Joins to `clients` on `client_id`, to `prices` and `companies` on `ticker`.

| Column | Type | |
|---|---|---|
| `client_id` | INTEGER | → `clients.id` |
| `ticker` | VARCHAR | |
| `shares` | FLOAT | |
| `purchase_date` | DATE | |
| `purchase_price` | FLOAT | |
| `sale_date` | DATE | null while open |
| `sale_price` | FLOAT | |
| `dividends` | FLOAT | |
| `dividend_pct` | FLOAT | |

`get_client_positions()` aggregates by ticker — `SUM(shares)`, `AVG(purchase_price)` — so several buys of the same name collapse into one position at average cost.

---

## Layer 2 — Screening and Scoring

### `companies` — the authoritative attributes table

The reference every other table joins to for sector and company type.

| Column | Type | |
|---|---|---|
| `ticker` | VARCHAR | join key |
| `name` | VARCHAR | |
| `sector` | VARCHAR | GICS-style, drives sector-neutral ranking |
| `industry` | VARCHAR | finer than sector |
| `company_type` | VARCHAR | `Early-Stage` \| `High-Growth` \| `Mature` — selects pillar weights |
| `as_of_date` | DATE | when this version became true |

**This is a slowly changing dimension.** Rows are appended, never updated. `append_company()` compares against the latest row and writes only when an attribute actually changed, so the table records what the *company* did rather than when the *script ran*.

Reads go through `get_company_attributes(conn, ticker, as_of_date)`:

```sql
WHERE ticker = ? AND as_of_date <= ?
ORDER BY as_of_date DESC
LIMIT 1
```

**Why this matters:** `company_type` selects the pillar weights. A company reclassifying Early-Stage → Mature changes how it's scored. Overwriting would mean a 2023 backtest scoring companies with their 2026 classification — a subtle, invisible look-ahead. `get_company_history()` returns the full audit trail.

> ⚠️ **Schema drift.** The live `companies` table still has the pre-`as_of_date` schema and holds 2 duplicate AMZN rows from before the change. `CREATE TABLE IF NOT EXISTS` won't alter an existing table, so it must be dropped and rebuilt before the current code will run.

### `qualitative_thesis`

The 4-pillar analyst judgement. One row per thesis.

| Column | Type | |
|---|---|---|
| `company_name` `ticker` `analyst` | VARCHAR | |
| `date` | DATE | |
| `company_type` | VARCHAR | |
| `leadership_score` `industry_growth_score` `moat_score` `macro_score` | FLOAT | 0-100 |
| `leadership_insights` … `macro_insights` | VARCHAR | reasoning behind each score |
| `status` | VARCHAR | |
| `price_target` | FLOAT | |

Scores are 0-100. Pillar *weights* live in `criteria.yaml` and are normalized to sum to 1.0 at load, so `Σ(score × weight)` lands back on a 0-100 scale.

**Open question:** `company_type` is duplicated from `companies`. Unlike the fundamentals case, there's an argument for keeping it — a thesis was scored under the weights implied by its type *at the time of writing*. Snapshotting preserves that; joining would retroactively rescore old theses. Not yet decided.

### `fundamentals_raw` — planned

Raw line items straight from SEC filings. Nothing computed.

Mirrors `FundamentalsRaw`: `ticker`, `fiscal_period_end`, `filing_available_date`, then ~21 line items (revenue, cogs, ebit, ebitda, net_income, cfo, capex, total_assets, total_liabilities, current_assets, current_liabilities, retained_earnings, cash, total_debt, preferred_equity, shares_outstanding, dividends_paid, buybacks, debt_repaid, interest_expense).

**Two dates, not one:**

| | |
|---|---|
| `fiscal_period_end` | the period the numbers describe |
| `filing_available_date` | when they became public — EDGAR's `filed` field |

Scoring must filter on `filing_available_date`, never `fiscal_period_end`. A quarter ending March 31 isn't public until mid-May; using the period end would trade on information nobody had. See [edgar_coverage.md](edgar_coverage.md).

**Store raw, compute derived.** Every metric — margins, GPA, the Altman ratios — is recomputable from these columns. Changing a formula never requires re-fetching.

**Deduplication:** the same period appears in multiple filings as restatements. For point-in-time honesty, keep the row with the **earliest** `filed` per `fiscal_period_end` — that's what was knowable at the time.

### `fundamentals` — planned

Computed metrics, one wide row per company-period. ~40 columns flattened from `QuantFundamentalData`'s five nested groups (valuation, quality, health, growth, capital return), with `AltmanZScore` unwrapped from inside `health`.

Deliberately carries **no `sector` or `company_type`** — those join from `companies`.

Column names must match the pydantic field names exactly, so a `model_dump()` flatten can build the INSERT from dict keys instead of 40 hand-maintained placeholders.

---

## How it joins

```
                    companies (SCD)
                    ticker · sector · company_type · as_of_date
                          │
        ┌─────────────────┼──────────────────┬────────────────────┐
        │                 │                  │                    │
    holdings          prices          fundamentals_raw    qualitative_thesis
    client_id         ticker·date     ticker·period       ticker
    ticker                                  │
        │                                   ▼
        ▼                             fundamentals
    clients                           (computed metrics)
    id
```

`prices` and `fundamentals` meet at the valuation metrics. `shares_outstanding` (EDGAR) × `close` (yfinance) = market cap, which four valuation ratios and the fourth Altman component depend on. **Neither source alone is sufficient.**

---

## Conventions

**Missing data.** Distinguish three cases:

| Case | Handling |
|---|---|
| Not yet fetched | `NULL` |
| Filed as zero | `0.0` |
| Not applicable to the sector | excluded from scoring, never imputed |

Only the first deserves a median substitute at ranking time. Assigning `0.0` to an unknown Altman component drags a healthy company toward false distress; assigning the median to a metric the sector doesn't have gives a bank a score on enterprise multiples it doesn't possess.

**Types.** Money is `FLOAT`, share counts `FLOAT` (splits produce fractions), dates `DATE` never `VARCHAR` — text dates sort alphabetically, which breaks every `ORDER BY as_of_date` in the schema.

**Idempotence.** Ingestion scripts run repeatedly. `companies` is safe (change detection). `prices` and `holdings` are **not** — re-running duplicates rows.

---

## Known issues

| | |
|---|---|
| `companies` schema drift | live table predates `as_of_date` and holds 2 duplicate AMZN rows; needs drop + rebuild |
| `clients.id` vs `Client.client_id` | positional insert hides the mismatch; breaks on `SELECT *` → model |
| `prices` has no uniqueness constraint | re-ingesting a cached range duplicates rows |
| `holdings` has no constraint | same |
| `scripts/setup_db.py` is empty | README instructs users to run it |

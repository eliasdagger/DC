# Dagher Capital — System Architecture

## Overview

Quantitative investment platform, built in layers. Each depends only on the ones below it.

| Layer | Purpose | Status |
|---|---|---|
| **1. Portfolio Analytics** | Client holdings, returns, risk metrics, reporting | ✅ working |
| **2. Investment Screening (MCDA)** | Quant + qualitative scoring of a stock universe | 🔨 foundation built, algorithms in progress |
| **3. Portfolio Optimization** | Constrained allocation with risk modeling | ⬜ not started |
| **4. Trading Algorithm** | Execution | ⬜ not started |

Layer 2 is where the current work is. It's also where the first strategy — **Value Investing** — lives; the design anticipates more strategies later, each scoring the same underlying data differently.

---

## Data flow

```
  EXTERNAL                 PERSISTENCE                  COMPUTATION
  ────────                 ───────────                  ───────────

  yfinance ──────────────► prices ──────────────────► returns.py
  (market prices)          ticker·date·OHLCV           positions.py
       │                        │                      reporting.py
       │                        │                          │
       │                        ▼                          ▼
       │                   market cap ◄──┐            LAYER 1 OUTPUT
       │                                 │            client reports
  SEC EDGAR ─────────────► fundamentals_raw
  (filings, as-filed)      raw line items
                                │
                                ▼
                           fundamentals ──────────────► screening.py
                           computed metrics             scoring.py
                                │                           │
  analyst ───────────────► qualitative_thesis ─────────────►│
  (4 pillars, 0-100)                                        │
                                                            ▼
                           companies (SCD) ───────────► LAYER 2 OUTPUT
                           sector · company_type        ranked universe
```

`companies` sits to the side deliberately — it's a reference table everything joins to, not a stage in the pipeline.

**Market cap needs both sources.** `shares_outstanding` comes from EDGAR, `close` from yfinance. Four valuation ratios and the fourth Altman component depend on the product. Neither source alone is sufficient.

---

## Module layout

```
src/
  data/          Layer 1 persistence + ingestion
    ingestion.py     yfinance → prices
    companies.py     company attributes (slowly changing dimension)
    clients.py       client records
    holdings.py      positions
    fundamentals.py  SEC EDGAR → fundamentals_raw
    engine.py        entry point; owns the DuckDB connection

  features/      calculations over prices
    returns.py       simple/log/cumulative/annualized, volatility, Sharpe, drawdown

  portfolio/     client-level aggregation
    positions.py     position table, portfolio value, portfolio Sharpe
    reporting.py     terminal report

  mcda/          Layer 2
    quant.py         store/retrieve computed fundamentals
    qual.py          store/retrieve analyst theses
    screening.py     absolute cutoffs (Altman Z, liquidity)
    scoring.py       percentile ranks, sector-neutral, pillar weights
    sensitivity.py   Monte Carlo over the scoring inputs

  utils/
    stock_models.py       securities analysis schemas
    operations_models.py  client / portfolio schemas
    config.py             paths, env, criteria loader

configs/
  criteria.yaml    pillar weights, screening thresholds
  xbrl_tags.yaml   EDGAR tag map
```

**The `stock_models` / `operations_models` split:** anything describing a *security* or its behaviour goes in the first; anything describing *clients and portfolios* goes in the second. `operations_models` imports from `stock_models`, never the reverse — portfolios know about stocks, stocks don't know about portfolios.

---

## Design decisions

### Point-in-time correctness

The system must be able to answer *"what did we know on date X"*, not just *"what is true now"*. Backtests are worthless otherwise — they'd score 2023 using 2026 information and produce returns nobody could have earned.

Three mechanisms:

1. **`fundamentals_raw` carries two dates.** `fiscal_period_end` (what the numbers describe) and `filing_available_date` (when they became public). Scoring filters on the second. A quarter ending March 31 isn't knowable until mid-May.

2. **`companies` is a slowly changing dimension.** Attributes append with an `as_of_date`; reads take the latest row on or before the query date. A company reclassifying Early-Stage → Mature changes its pillar weights, so overwriting would retroactively rescore history.

3. **Restatements are dropped.** EDGAR reports the same period from multiple filings as companies revise figures. Keeping the *earliest* `filed` per period preserves what was originally reported — the number the market actually saw.

### Single source of truth

Sector and company type live only on `companies`. `QuantFundamentalData` deliberately omits them. One company has one sector; stating it twice guarantees they eventually disagree, and nothing would tell you which is right.

### Raw before derived

`fundamentals_raw` stores filing line items; `fundamentals` stores computed metrics. Changing a formula — or fixing a bug in one — means recomputing, never re-fetching. It also means a metric can be derived multiple ways with a fallback chain (`gross_profit` from a tag where filed, from `revenue − cogs` where not).

### Config over code

Pillar weights, screening thresholds, and the EDGAR tag map live in `configs/*.yaml`. These are the values most likely to change, and they should change without editing code — partly for convenience, partly because tuning them in code invites tuning them until the backtest looks good, which is the overfitting failure the methodology warns about.

Weights are stored raw and normalized at load, so any single weight can be edited without rebalancing the others.

### Absolute screening, relative ranking

Two different questions, handled differently:

- **Screening** asks "is this company financially sound?" — a binary survival test against an absolute threshold (Altman Z < 1.81 is distress regardless of peers). It eliminates; it does not rank.
- **Ranking** asks "is this cheaper than the alternatives?" — inherently relative, done by percentile within sector.

Following Gray for the first and O'Shaughnessy for the second.

### Sector-relative, not market-relative

Ranking `debt_equity` across the whole market just sorts by sector — every bank lands at the bottom, and the ranking says nothing about which bank is well run. Percentile ranks are computed **within sector**.

But ranking within sector doesn't rescue a metric that's *meaningless* for that sector. A bank's enterprise value is nonsense because debt is its raw material. Those metrics are excluded and the composite renormalizes. See [sector_applicability.md](sector_applicability.md).

---

## Layer 2 pipeline

```
1. Company attributes    →  companies        ✅ done
2. Ingest fundamentals   →  fundamentals_raw 🔨 in progress
3. Screen                →  eliminate distress, illiquidity
4. Sector-relative ranks →  percentile within sector
5. Company-type weights  →  qualitative composite
6. Sensitivity           →  Monte Carlo over weights, scores, classification
```

Steps 3-6 are scaffolded with documented stubs in `src/mcda/`.

Step 6 varies three things, not one: the pillar **weights**, the analyst **pillar scores** (subjective judgements with real uncertainty), and the **company-type classification** — which is the largest single lever, since reclassifying swaps the entire weight vector on one discrete judgement.

---

## Known constraints

**yfinance** is unofficial and scrapes undocumented endpoints. Fine for prices, which are re-fetchable. Not used for fundamentals: it provides no filing dates and returns restated figures, both fatal to point-in-time correctness.

**SEC EDGAR** is the fundamentals source — free, official, as-filed, with filing dates. The cost is normalization: tag names vary by company and change with accounting standards. See [edgar_coverage.md](edgar_coverage.md).

**Ticker → CIK is not stable.** After a holding-company reorganization the ticker moves to the new entity while history stays under the old CIK. Overrides live in `configs/xbrl_tags.yaml`.

**Some metrics are unattainable per sector**, structurally. Banks file no working capital, so Altman Z cannot be computed for them at all. This is a fact about bank accounting, not a data gap to be closed.

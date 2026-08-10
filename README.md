# Dagher Capital — Quantitative Investment Platform

A Python-based quantitative investment system powering Dagher Capital's portfolio analytics, investment research, and optimization.

## Overview

**Layer 1: Portfolio Analytics** — Client holdings, returns, risk metrics  
**Layer 2: Investment Screening** — MCDA-based thesis evaluation with Monte Carlo sensitivity  
**Layer 3: Portfolio Optimization** — Constrained allocation engine with risk modeling

## Quick Start

```bash
# Clone
git clone https://github.com/eliasdagger/DC.git
cd DC

# Install
pip install -r requirements.txt

# Setup database
python scripts/setup_db.py

# Run tests
pytest tests/
```

## Project Structure

- `src/data/` — Layer 1 persistence: prices, clients, holdings, company attributes
- `src/features/` — Return and volatility calculations
- `src/portfolio/` — Positions, portfolio metrics, client reporting
- `src/mcda/` — Layer 2 screening and scoring (quant, qual, screening, scoring, sensitivity)
- `src/utils/` — Pydantic schemas and configuration
- `src/optimizer/` — Layer 3 allocation engine
- `configs/` — Tunable criteria (pillar weights, screening thresholds)
- `notebooks/` — Exploratory analysis and development
- `tests/` — Unit tests
- `data/` — Raw and processed data
- `docs/` — Architecture and methodology documentation

## Tech Stack

- **Python** — Core language
- **DuckDB** — Analytical database
- **pandas / NumPy** — Data manipulation and math
- **yfinance** — Market data
- **Pydantic** — Data validation
- **Matplotlib / Plotly** — Visualization
- **pytest** — Testing

## Implementation Progress

### Week 1 — Data Ingestion ✅
- [x] Define Pydantic models (Stock, Client)
- [x] Implement yfinance API fetching
- [x] Build DuckDB caching layer
- [x] Test end-to-end with real stock data

**What works:**
- `get_prices()` — fetches OHLCV data from yfinance
- `cache_prices()` — stores prices in DuckDB
- `get_cached_price()` — retrieves cached prices

**Database:** `prices` table with columns: ticker, date, open, high, low, close, volume

---

### Week 2 — Return Calculations ✅
- [x] Implement simple return calculations
- [x] Implement log return calculations
- [x] Implement cumulative return calculations
- [x] Implement annualized return calculations
- [x] Implement volatility calculations

**What works:**
- `simple_returns()` — daily percentage returns
- `log_returns()` — logarithmic returns
- `cumulative_returns()` — total return over period
- `annualized_return()` — return scaled to yearly basis
- `volatility()` — annualized standard deviation

---

### Week 3-5 — Portfolio Metrics & Reporting ✅
- [x] Sharpe ratio calculation
- [x] Drawdown analysis
- [x] Position tracking
- [x] Client report generation

**What works:**
- `sharpe_ratio()` — risk-adjusted return for a single ticker
- `max_drawdown()` — largest peak-to-trough decline
- `get_client_positions()` — live position table with cost basis, value, unrealized gain, weight
- `portfolio_value()` / `portfolio_sharpe()` — aggregate portfolio metrics
- `generate_report()` — formatted terminal report per client

**Database:** `clients` and `holdings` tables, both driven through `src/data/engine.py`

---

### Week 6 — Testing & Project Hygiene ✅
- [x] pytest suite covering objects, ingestion, storage, and calculations
- [x] Package the project (`pyproject.toml`) so `src.*` imports resolve without path hacks
- [x] Type-hint cleanup — optional fields declared `Optional[X]` rather than defaulting to invalid types

---

### Week 7 — Layer 2 Foundation: Schemas & Config ✅
- [x] Split models by domain — `stock_models.py` (securities analysis) and `operations_models.py` (clients, portfolios)
- [x] Define the quantitative metric vocabulary: valuation, quality, health, growth, capital return
- [x] Define `FundamentalsRaw` — raw filing inputs, kept separate from computed metrics so anything can be recalculated without re-fetching
- [x] Define `QualInvestmentThesis` — 4-pillar qualitative judgement
- [x] Externalize tunable parameters to `configs/criteria.yaml`, loaded via `load_criteria()`
- [x] Restructure `src/mcda/` into quant / qual / screening / scoring

**Design decisions:**
- **Point-in-time correctness** — `QuantFundamentalData` carries both `fiscal_period_end` and `filing_available_date`. A quarter ending March 31 isn't public until mid-May; scoring on it earlier is trading on the future.
- **Single source of truth** — sector and company type live only on `Company` and are joined on `ticker`. No table carries its own copy.
- **Weights as config** — pillar weights are normalized at load, so any single weight can change without rebalancing the rest.

---

### Week 8 — Company Attributes & Thesis Storage ✅
- [x] `companies` table as a slowly changing dimension
- [x] Point-in-time attribute lookup
- [x] Change detection — re-running ingest with unchanged data appends nothing
- [x] `qualitative_thesis` table for storing 4-pillar analyst theses

**What works:**
- `append_company()` — appends only on a real change, so history records what the company did, not when the script ran
- `get_company_attributes(conn, ticker, as_of_date)` — attributes as they stood on a given date
- `get_company_history()` — every recorded version of a company, one row per change
- `create_theses_table()` / `cache_analysis()` / `get_thesis()` — qualitative thesis persistence
- `get_weighting()` — pillar weights for a company type, normalized to 1.0

**Why history matters:** a company reclassifying from Early-Stage to Mature changes which pillar weights apply. Overwriting would make every backtest score historical periods with today's classification.

---

### Week 9 — Fundamentals Ingestion (In Progress)
- [ ] `fundamentals_raw` table — persist raw filing data
- [ ] Flatten `QuantFundamentalData` into the wide `fundamentals` table
- [ ] Compute derived metrics (GPA, margins, Altman components) from raw inputs
- [ ] Apply the filing-lag rule so no metric is visible before it was knowable

---

### Upcoming — Screening & Scoring
- [ ] `altman_z_score()` — weighted sum of the five component ratios
- [ ] `screen_universe()` — absolute cutoffs, applied before any ranking
- [ ] `percentile_rank()` / `sector_neutral_rank()` — rank within sector, not across the market
- [ ] `calculate_pillar_scores()` — weighted qualitative composite
- [ ] `sensitivity.py` — Monte Carlo across weights, pillar scores, and company-type classification

## Roadmap

- [x] Layer 1: Data infrastructure & returns
- [x] Layer 1: Portfolio metrics & reporting
- [ ] Layer 2: MCDA investment screening — *foundation built, algorithms in progress*
- [ ] Layer 3: Portfolio optimizer
- [ ] Layer 4: Trading algorithm

## Documentation

See `docs/` for detailed architecture, schema, and methodology.

## Author

Built by Elie Dagher as Dagher Capital's quantitative infrastructure.
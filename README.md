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

- `src/` — Core modules (data, features, portfolio, MCDA, optimizer)
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

### Week 3-5 — Portfolio Metrics (In Progress)
- [ ] Sharpe ratio calculation
- [ ] Drawdown analysis
- [ ] Position tracking
- [ ] Auto-generate client cards
- [ ] Polish & testing

## Roadmap

- [x] Layer 1: Data infrastructure & returns
- [ ] Layer 1: Portfolio metrics & reporting
- [ ] Layer 2: MCDA investment screening
- [ ] Layer 3: Portfolio optimizer
- [ ] Layer 4: Trading algorithm

## Documentation

See `docs/` for detailed architecture, schema, and methodology.

## Author

Built by Elie Dagher as Dagher Capital's quantitative infrastructure.
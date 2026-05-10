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

## Usage

```python
import duckdb
from src.data.storage import initialize_db
from src.features.returns import compute_returns

conn = duckdb.connect('dagher.duckdb')
returns = compute_returns(conn, 'AAPL')
```

## Tech Stack

- **Python** — Core language
- **DuckDB** — Analytical database
- **pandas / NumPy** — Data manipulation and math
- **Pydantic** — Data validation
- **Jupyter** — Prototyping
- **Matplotlib / Plotly** — Visualization
- **pytest** — Testing

## Roadmap

- [x] Initial repo setup
- [ ] Layer 1: Portfolio analytics engine
- [ ] Layer 2: MCDA investment screening
- [ ] Layer 3: Portfolio optimizer
- [ ] Layer 4: Trading algorithm

## Documentation

See `docs/` for detailed architecture, schema, and methodology.

## Author

Built by Elie Dagher.
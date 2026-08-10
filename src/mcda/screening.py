"""
Module: Negative Screening

Problem:
Cheap companies are often cheap for a reason. Ranking the whole universe on
valuation without first removing financially distressed names produces a
portfolio of value traps.

Description:
Applies absolute cutoffs BEFORE any ranking happens. This step eliminates
companies outright — it does not score them down. Thresholds come from
configs/criteria.yaml so they can be tuned without editing code.

Key Functions:
- altman_z_score: Compute the Altman Z-score from its five component ratios
- screen_universe: Return the companies that survive all cutoffs

Dependencies:
- duckdb: Query the fundamentals table
- pandas: Data handling
- config: Read thresholds from criteria.yaml

Example:
    >>> z = altman_z_score(data.health.altman_z_score)
    >>> survivors = screen_universe(conn)

────────────────────────────────────────────────────────────────────────────
IMPLEMENTATION NOTES (step 3 of the Layer 2 plan — write these yourself)

The Altman Z-score is a weighted sum of the five ratios already stored on the
AltmanZScore model:

    Z = 1.2 * working_capital_total_assets
      + 1.4 * retained_earnings_total_assets
      + 3.3 * ebit_total_assets
      + 0.6 * market_cap_total_liabilities
      + 1.0 * sales_total_assets

Zones:
    Z > 2.99          safe
    1.81 < Z < 2.99   grey zone
    Z < 1.81          distress    <- criteria.yaml: screening.altman_z_min

Two things worth handling deliberately:

1. Missing components. Every ratio on AltmanZScore is Optional. Decide what a
   partial Z-score means — returning None is more honest than silently
   treating a missing ratio as 0.0, which would drag the score toward distress
   and eliminate a healthy company on an API gap.

2. Sector validity. Z-scores are not meaningful for banks, insurers, or REITs —
   their balance sheets work differently, so 'working capital' and 'total
   liabilities' don't mean the same thing. Screen those sectors on their own
   terms or exclude them from this test rather than failing them by default.

screen_universe should read altman_z_min and min_liquidity_pctile from
load_criteria() rather than hardcoding 1.81.
────────────────────────────────────────────────────────────────────────────
"""

from typing import Optional

import pandas as pd
import duckdb as dd

from src.utils.stock_models import AltmanZScore
from src.utils.config import load_criteria


def altman_z_score(components: AltmanZScore) -> Optional[float]:
    """Weighted sum of the five Altman ratios. Lower = more distressed."""
    pass


def screen_universe(conn: dd.DuckDBPyConnection) -> pd.DataFrame:
    """Return companies that pass the distress and liquidity cutoffs."""
    pass

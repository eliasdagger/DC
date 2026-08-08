"""
Module: MCDA Scoring

Problem:
A company has ~41 quantitative metrics and 4 qualitative pillar scores. Those
can't be compared across companies directly — a P/E of 15 means something very
different for a bank than for a software company, and a moat score of 7 means
nothing without knowing what kind of company is being judged.

Description:
Turns raw metrics into comparable scores. Metrics are ranked within their own
sector (so like is compared to like), and qualitative pillars are weighted by
company type (macro matters more for an early-stage company than a mature one).

Key Functions:
- get_weighting: Pillar weights for a company type, normalized to sum to 1.0
- calculate_pillar_scores: Weighted qualitative score for one company
- percentile_rank: Convert raw metric values to 1-100 percentiles
- sector_neutral_rank: Percentile-rank a metric within each sector

Dependencies:
- duckdb: Query the theses and fundamentals tables
- pandas: Ranking and data handling
- config: Read pillar weights from criteria.yaml

Example:
    >>> get_weighting("Mature")
    leadership         0.071429
    industry_growth    0.285714
    moat               0.357143
    macro              0.285714
    dtype: float64
"""

import pandas as pd
import duckdb as dd

from src.utils.config import load_criteria


def get_weighting(company_type: str) -> pd.Series:
    """Return the 4 qualitative pillar weights for a company type.

    Weights in criteria.yaml are raw numbers, not percentages. They get
    normalized here so they always sum to 1.0 — meaning you can edit one
    number in the YAML without rebalancing the rest.
    """
    criteria = load_criteria()
    weights = criteria["pillar_weights"]

    if company_type not in weights:
        raise ValueError(
            f"Unknown company_type '{company_type}'. "
            f"Expected one of: {list(weights.keys())}"
        )

    raw = pd.Series(weights[company_type])
    return raw / raw.sum()


def calculate_pillar_scores(conn: dd.DuckDBPyConnection, ticker: str) -> float:
    """Weighted qualitative score: pillar scores x company-type weights.

    ────────────────────────────────────────────────────────────────────────
    IMPLEMENTATION NOTES (step 5 — write this yourself)

    Shape of the work:
      1. Query the 4 pillar scores + company_type from the 'theses' table
      2. weights = get_weighting(company_type)
      3. Multiply pillar scores by their weights and sum

    Two bugs from the previous version worth not reintroducing:

      - The old code built a (sql_string, params) TUPLE and then called .df()
        on it. A tuple has no .df(). The query has to actually go through
        conn.execute(sql, params).df().

      - The old code read company_data['Company_Type']. DuckDB returns the
        column name as it was defined — lowercase 'company_type'. Pandas
        column lookup is case-sensitive, so the capitalized version raises
        KeyError.

    Also worth deciding: the pillar scores are Optional on the model. If an
    analyst filled in 3 of 4 pillars, does the score use the 3 they have
    (renormalizing the weights), or refuse to score at all? Both are
    defensible — pick one on purpose.
    ────────────────────────────────────────────────────────────────────────
    """
    pass


def percentile_rank(values: pd.Series) -> pd.Series:
    """Convert raw metric values to 1-100 percentiles.

    ────────────────────────────────────────────────────────────────────────
    IMPLEMENTATION NOTES (step 4 — write this yourself)

    Why percentiles rather than raw values: raw fundamentals are full of
    extremes. One company with near-zero earnings produces a P/E of 10,000 and
    distorts any average it touches. Ranking flattens that — the outlier is
    simply 'worst', not 'worst by a factor of 400'.

    pandas gives you this directly: .rank(pct=True) returns 0-1, multiply by
    100 for a 1-100 scale.

    Missing data: assign the median (50) rather than dropping the company.
    A missing P/E shouldn't eliminate an otherwise strong company from the
    universe — it should just not count for or against it on that one metric.
    ────────────────────────────────────────────────────────────────────────
    """
    pass


def sector_neutral_rank(df: pd.DataFrame, metric: str, sector_col: str = "sector") -> pd.Series:
    """Percentile-rank a metric within each sector rather than across the whole universe.

    ────────────────────────────────────────────────────────────────────────
    IMPLEMENTATION NOTES (step 4 — write this yourself)

    Why this matters: banks carry structurally more leverage than software
    companies, and utilities structurally more debt than either. Ranking
    debt_equity across the whole market just sorts by sector — every bank
    lands at the bottom, and the ranking tells you nothing about which bank
    is well run.

    Ranking within sector asks the useful question instead: is this bank
    cheap RELATIVE TO OTHER BANKS?

    pandas shape for this: df.groupby(sector_col)[metric].rank(pct=True)

    Watch for thin sectors. If a sector has 3 companies, the percentile ranks
    are 33/67/100 regardless of how similar they actually are — the spread is
    an artifact of the group size, not a real signal.
    ────────────────────────────────────────────────────────────────────────
    """
    pass

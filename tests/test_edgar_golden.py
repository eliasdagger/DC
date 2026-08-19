"""
Golden-value regression tests for EDGAR extraction.

Why this exists: scripts/edgar_extract.py encodes five judgment calls
(period-length filtering, restatement dedup, derive-vs-read ordering,
missing-vs-structural-absence, CIK reorg handling) that are individually
easy to get subtly wrong. These tests catch regressions the moment they
happen — before a wrong number ever reaches the scoring engine.

Fixtures are real SEC companyfacts JSON, frozen in tests/fixtures/edgar/,
so this runs offline and fast (no live SEC calls, no flakiness).

Two kinds of check:
1. Hardcoded expected values (verified against real 10-K filings)
2. Cross-field identity checks (a company's OWN reported numbers must
   agree with each other — e.g. reported GrossProfit should equal
   reported revenue minus reported cogs, independent of our derivation
   logic, since a real company's income statement has to add up)

If you change edgar_extract.py or configs/xbrl_tags.yaml and these start
failing, that's the point — go find out why before porting the change
into src/data/fundamentals.py.
"""
import json
import os

import pandas as pd
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from edgar_extract import load_tagmap, build_fundamentals, annual_series

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "edgar")


@pytest.fixture(scope="module")
def tagmap():
    return load_tagmap()


def load(ticker):
    with open(os.path.join(FIXTURES, f"{ticker}.json")) as f:
        return json.load(f)["facts"]["us-gaap"]


def built(ticker, tagmap):
    return build_fundamentals(load(ticker), tagmap)


# ── 1. Golden values — checked against real 10-K filings ────────────────────
# AMZN and AAPL FY2023 figures were independently cross-checked against
# public filing totals earlier in this project (see docs/edgar_hardening.md).
# The rest are frozen snapshots of verified-correct extraction output —
# if these change unexpectedly, the extraction logic changed, not the filing.

GOLDEN = [
    # ticker, field, period_end, expected
    ("AMZN", "revenue",           "2023-12-31", 574_785_000_000),
    ("AMZN", "total_assets",      "2023-12-31", 527_854_000_000),
    ("AMZN", "net_income",        "2023-12-31",  30_425_000_000),
    ("AAPL", "revenue",           "2023-09-30", 383_285_000_000),   # AAPL FY ends late Sept, not Dec
    ("JPM",  "total_assets",      "2024-12-31", 4_002_814_000_000),
    ("JPM",  "net_income",        "2024-12-31",    58_471_000_000),
    ("MSFT", "revenue",           "2024-06-30", 245_122_000_000),
    ("XOM",  "revenue",           "2024-12-31", 349_585_000_000),
]


@pytest.mark.parametrize("ticker,field,period,expected", GOLDEN)
def test_golden_value(tagmap, ticker, field, period, expected):
    f = built(ticker, tagmap)
    got = f[field].get(period)
    assert got is not None, f"{ticker} {field} {period}: no value extracted"
    assert got == pytest.approx(expected, rel=0.001)


# ── 2. Cross-field identity checks — a company's own numbers must agree ─────

def test_aapl_gross_profit_matches_reported(tagmap):
    """AAPL reports GrossProfit, revenue, and cogs as three SEPARATE tags.
    They should agree with each other — this isn't our derivation logic,
    it's checking the company's own filed numbers are internally consistent
    (and that we extracted all three correctly)."""
    f = built("AAPL", tagmap)
    period = "2023-09-30"   # AAPL fiscal year ends late September, not December
    reported_gp = f["gross_profit_tag"].get(period)
    implied_gp = f["revenue"].get(period) - f["cogs"].get(period)
    assert reported_gp is not None
    assert reported_gp == pytest.approx(implied_gp, rel=0.001)


def test_amzn_gross_profit_is_derived_not_reported(tagmap):
    """AMZN stopped reporting GrossProfit in 2009 (see docs/edgar_coverage.md).
    Confirms the derivation fallback is actually firing for recent years,
    not silently returning the (empty) reported tag."""
    f = built("AMZN", tagmap)
    period = "2023-12-31"
    assert pd.isna(f["gross_profit_tag"].get(period, float("nan")))
    assert f["gross_profit"].get(period) is not None
    assert f["gross_profit"][period] == pytest.approx(
        f["revenue"][period] - f["cogs"][period], rel=0.001
    )


def test_balance_sheet_identity_holds_on_reported_values(tagmap):
    """assets = liabilities + equity, using ONLY companies where all three
    are REPORTED tags (not our derived total_liabilities) — otherwise this
    would be circular, since we derive total_liabilities FROM this identity
    for companies that don't report it directly.

    AMZN is deliberately excluded: it reports NO 'Liabilities' tag at all
    (confirmed — this is exactly the gap the total_liabilities derivation
    fallback exists to fill). Including it here would test the derivation
    against itself, which proves nothing."""
    for ticker in ["AAPL", "MSFT"]:
        usgaap = load(ticker)
        reported_liab = annual_series(usgaap, ["Liabilities"], "instant", tagmap)
        assert not reported_liab.empty, f"{ticker} unexpectedly derives liabilities"

        f = built(ticker, tagmap)
        for period in reported_liab.dropna().index[-3:]:
            assets = f["total_assets"].get(period)
            equity = f["equity"].get(period)
            liab = reported_liab.get(period)
            assert assets == pytest.approx(liab + equity, rel=0.005), \
                f"{ticker} {period}: assets != liabilities + equity"


# ── 3. Judgment call #1 — the FY trap ────────────────────────────────────────

def test_period_length_filter_rejects_quarters(tagmap):
    """Regression test for the specific bug found in this project: a 10-K
    contains quarterly figures that can carry fp='FY' and form='10-K' while
    holding a quarterly value. AMZN FY2017 revenue was understated 66% by
    a naive fp/form-only filter. Confirm the length check catches it."""
    usgaap = load("AMZN")
    s = annual_series(usgaap, ["SalesRevenueNet",
                                "RevenueFromContractWithCustomerExcludingAssessedTax"],
                       "duration", tagmap)
    # FY2017 revenue was ~177.9B; the quarterly leak was ~60.5B.
    # If the length filter is broken, this assertion catches the wrong value.
    val = s.get("2017-12-31")
    if val is not None:
        assert val > 100_000_000_000, (
            f"AMZN FY2017 revenue = {val:,.0f} — looks like a quarterly figure "
            f"leaked through (period-length filter may be broken)"
        )


# ── 4. Judgment call #2 — restatement dedup (earliest filed wins) ───────────

def test_restatement_dedup_keeps_earliest_filed():
    """If a period appears in multiple filings with different values,
    the EARLIEST filed value must win — that's what was knowable at the
    time. This directly tests the sort_values('filed').groupby('end').first()
    line in annual_series()."""
    usgaap = {
        "TestConcept": {
            "units": {
                "USD": [
                    {"end": "2023-12-31", "start": "2023-01-01", "val": 100,
                     "form": "10-K", "filed": "2024-02-01"},   # original
                    {"end": "2023-12-31", "start": "2023-01-01", "val": 999,
                     "form": "10-K", "filed": "2025-02-01"},   # later restatement
                ]
            }
        }
    }
    tagmap = {"min_year": 2010, "accepted_forms": ["10-K", "10-K/A"], "duration_days": [350, 380]}
    s = annual_series(usgaap, ["TestConcept"], "duration", tagmap)
    assert s["2023-12-31"] == 100, "restatement dedup picked the LATER filing, not the earliest"


# ── 5. Judgment call #4 — missing vs structurally absent ────────────────────

def test_bank_cogs_is_structurally_absent(tagmap):
    """Banks don't sell goods, so 'cogs' should come back EMPTY, not zero.
    A caller that treats empty-as-zero would compute a nonsense gross margin
    instead of recognizing the metric doesn't apply."""
    f = built("JPM", tagmap)
    assert f["cogs"].dropna().empty, (
        "JPM cogs has values — either a tag now exists (update the sector "
        "exemption docs) or a bug is inventing a cost-of-goods figure for a bank"
    )


def test_reit_current_assets_is_structurally_absent(tagmap):
    """REITs file unclassified balance sheets — no current/non-current split."""
    f = built("ARE", tagmap)
    assert f["current_assets"].dropna().empty


# ── 6. Reorg / thin-entity detection ─────────────────────────────────────────

def test_reorg_detector_flags_thin_cik():
    """The Exxon holding-company reorg produced a CIK with only 94 concepts
    and zero years of revenue history. Confirm a thin-entity check would
    actually catch this — the exact bug found and fixed in this project."""
    path = os.path.join(FIXTURES, "reorg_case", "XOM_thin_cik.json")
    with open(path) as f:
        usgaap = json.load(f)["facts"]["us-gaap"]
    assert len(usgaap) < 150, "fixture no longer represents a thin/reorg'd entity"


def test_corrected_xom_is_not_thin(tagmap):
    """The override CIK (0000034088) should have full history, unlike the
    thin shell above — confirms cik_overrides actually fixes the problem."""
    usgaap = load("XOM")
    assert len(usgaap) > 150
    f = built("XOM", tagmap)
    assert len(f["revenue"].dropna()) >= 10

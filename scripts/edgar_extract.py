"""
Module: EDGAR Extraction — reference implementation

Problem:
The tag-matching, period-length filtering, restatement dedup, and derivation
logic from the study scripts (02-04, 08) needs to live somewhere importable —
both for tests and as the reference you port into src/data/fundamentals.py.

Description:
Pure functions, no side effects, no printing, no top-level execution. Loads
its tag map from configs/xbrl_tags.yaml (the authoritative source) rather
than hardcoding a copy, so a change to the YAML is picked up automatically —
including the receivables/net_ppe/sga fields added for Beneish M-Score.

This is the SAME logic verified in scripts/04_validate.py and
scripts/verify_pipeline.py (AMZN/AAPL/JPM figures checked against real 10-Ks).
Nothing here is new logic — it's that logic, made importable.

Key Functions:
- load_tagmap: read configs/xbrl_tags.yaml
- annual_series: one field's time series for one company (tag fallback +
  period-length filter + restatement dedup)
- build_fundamentals: every field for one company, including derivations

The five judgment calls (see docs/edgar_coverage.md, docs/edgar_hardening.md)
live in annual_series() and build_fundamentals(). Read these two functions
closely before writing fundamentals.py — this is 90% of that module already
written correctly, waiting to be ported with your own DuckDB storage layer.

Dependencies:
- pandas: time-series alignment (combine_first)
- pyyaml: tag map

Example:
    >>> tagmap = load_tagmap()
    >>> usgaap = json.load(open("AMZN.json"))["facts"]["us-gaap"]
    >>> f = build_fundamentals(usgaap, tagmap)
    >>> f["revenue"].loc["2023-12-31"]
    574785000000.0
"""
import os

import pandas as pd
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "xbrl_tags.yaml")


def load_tagmap(path: str = CONFIG_PATH) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def annual_series(usgaap: dict, tags: list, kind: str, tagmap: dict) -> pd.Series:
    """One field's clean annual time series, walking a candidate tag list.

    Judgment call #1 (period length): for 'duration' concepts, a record is
    kept only if its span is 350-380 days. Without this, quarterly figures
    inside a 10-K that are mislabeled fp='FY' leak in and corrupt the series
    (verified case: AMZN 2017 revenue understated 66% without this filter).

    Judgment call #2 (restatement dedup): sort by 'filed' date ascending,
    keep the FIRST value per period end. That's "what was known at the
    time" — the point-in-time-correct choice. Reversing to .last() would
    silently introduce look-ahead bias.

    Judgment call #4a (structural absence): a field with zero coverage
    across a whole tag list returns an EMPTY series, not zeros. Distinguish
    that from "unknown" at the caller/scoring level — see xbrl_tags.yaml's
    per-field notes on which absences are structural (banks/cogs) vs real
    gaps to investigate.
    """
    min_year = str(tagmap.get("min_year", 2010))
    forms = tuple(tagmap.get("accepted_forms", ["10-K", "10-K/A"]))
    lo, hi = tagmap.get("duration_days", [350, 380])

    out = pd.Series(dtype=float)
    for tag in tags:
        if tag not in usgaap:
            continue
        units = usgaap[tag]["units"]
        unit_key = next((k for k in ("USD", "shares") if k in units), None)
        if unit_key is None:
            continue

        recs = []
        for p in units[unit_key]:
            if p.get("form") not in forms or p["end"][:4] < min_year:
                continue
            if kind == "duration":
                if "start" not in p:
                    continue
                days = (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days
                if not (lo <= days <= hi):
                    continue
            elif "start" in p:
                continue
            recs.append({"end": p["end"], "val": p["val"], "filed": p["filed"]})

        if recs:
            df = pd.DataFrame(recs).sort_values("filed").groupby("end").first()
            out = out.combine_first(df["val"])

    return out.sort_index()


def build_fundamentals(usgaap: dict, tagmap: dict) -> dict:
    """Every field, as a dict of {field_name: pd.Series}, including derivations.

    Judgment call #3 (derive vs read): each derivation uses combine_first,
    so a company's OWN reported figure always wins where it exists; the
    formula only fills periods the reported tag left empty. Getting the
    order backwards means computed values silently overwrite filed ones.
    """
    fields = tagmap["fields"]
    helpers = tagmap.get("helpers", {})

    f = {}
    for name, spec in fields.items():
        f[name] = annual_series(usgaap, spec["tags"], spec["kind"], tagmap)
    for name, spec in helpers.items():
        f[name] = annual_series(usgaap, spec["tags"], spec["kind"], tagmap)

    # Derivations — reported value first, formula fills the gaps.
    f["gross_profit"] = f.get("gross_profit_tag", pd.Series(dtype=float)) \
        .combine_first(f["revenue"] - f["cogs"])

    f["total_liabilities"] = f.get("total_liabilities_tag", pd.Series(dtype=float)) \
        .combine_first(f.get("liabilities_and_equity", pd.Series(dtype=float)) - f["equity"]) \
        .combine_first(f["total_assets"] - f["equity"])

    f["dep_amort"] = f.get("dep_amort_combined", pd.Series(dtype=float)) \
        .combine_first(
            f.get("depreciation_only", pd.Series(dtype=float))
             .add(f.get("amortization_only", pd.Series(dtype=float)), fill_value=0)
        )

    f["ebitda"] = f["ebit"] + f["dep_amort"]
    f["working_capital"] = f["current_assets"] - f["current_liabilities"]
    f["fcf"] = f["cfo"] - f["capex"]

    return f

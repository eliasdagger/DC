"""Data-quality matrix: for every company x every field, is it present /
derived / structurally-absent / missing? Then a per-company screenability
summary, so we know the actual usable universe before the scorer exists."""
import csv
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "big_cache")
PROJ = os.path.join("C:", os.sep, "Users", "elied", "Projects", "DC", "DC")
sys.path.insert(0, os.path.join(PROJ, "scripts"))
from edgar_extract import load_tagmap, build_fundamentals, annual_series

tagmap = load_tagmap()
universe = {c["ticker"]: c for c in json.load(open(os.path.join(HERE, "sp500_universe.json")))}

# Sector-structural absences confirmed in docs/sector_applicability.md —
# these are EXPECTED gaps, not data-quality problems.
STRUCTURAL = {
    "Financials": {"cogs", "gross_profit", "current_assets", "current_liabilities", "working_capital"},
    "REIT":       {"cogs", "gross_profit", "current_assets", "current_liabilities", "working_capital"},
}

REPORT_FIELDS = ["revenue", "cogs", "gross_profit", "ebit", "ebitda", "net_income", "cfo",
                  "capex", "fcf", "interest_expense", "dividends_paid", "buybacks",
                  "debt_repaid", "total_assets", "total_liabilities", "equity",
                  "current_assets", "current_liabilities", "working_capital",
                  "retained_earnings", "cash", "total_debt", "preferred_equity",
                  "shares_outstanding", "receivables", "net_ppe", "sga"]

# a reasonable minimum bar for "screenable" — enough of the core metrics to
# run Altman Z + basic valuation, for the most recent fiscal year
CORE_FOR_SCREENING = ["revenue", "net_income", "total_assets", "equity", "cash"]

rows = []
files = sorted(f[:-5] for f in os.listdir(CACHE) if f.endswith(".json"))
print(f"analyzing {len(files)} companies x {len(REPORT_FIELDS)} fields")

for i, tkr in enumerate(files, 1):
    if i % 100 == 0:
        print(f"  {i}/{len(files)}")
    meta = universe.get(tkr, {})
    sector = meta.get("sector", "?")
    with open(os.path.join(CACHE, f"{tkr}.json")) as fh:
        usgaap = json.load(fh)["facts"].get("us-gaap", {})

    f = build_fundamentals(usgaap, tagmap)

    row = {"ticker": tkr, "sector": sector, "total_concepts": len(usgaap)}
    present_count, missing_fields = 0, []
    for field in REPORT_FIELDS:
        s = f.get(field, pd.Series(dtype=float)).dropna()
        n_years = len(s)
        if field in STRUCTURAL.get(sector, set()):
            status = "N/A"           # structurally absent for this sector
        elif n_years == 0:
            status = "MISSING"
            missing_fields.append(field)
        elif n_years < 5:
            status = "THIN"
        else:
            status = "OK"
        row[field] = status
        if status in ("OK", "THIN", "N/A"):
            present_count += 1

    row["coverage_pct"] = round(100 * present_count / len(REPORT_FIELDS), 1)
    core_ok = sum(1 for c in CORE_FOR_SCREENING
                  if len(f.get(c, pd.Series(dtype=float)).dropna()) > 0)
    row["screenable"] = core_ok == len(CORE_FOR_SCREENING)
    row["missing_core"] = ",".join(c for c in CORE_FOR_SCREENING
                                    if len(f.get(c, pd.Series(dtype=float)).dropna()) == 0)
    rows.append(row)

df = pd.DataFrame(rows)
df.to_csv(os.path.join(HERE, "data_quality_matrix.csv"), index=False)

print(f"\n{'='*60}")
print(f"SCREENABLE (has revenue/net_income/assets/equity/cash): "
      f"{df['screenable'].sum()} / {len(df)}")
print(f"{'='*60}\n")

not_screenable = df[~df["screenable"]]
if len(not_screenable):
    print("NOT screenable — missing a core field:\n")
    for _, r in not_screenable.iterrows():
        print(f"  {r['ticker']:<6} {r['sector']:<12} missing: {r['missing_core']}")

print(f"\ncoverage_pct distribution:")
print(df["coverage_pct"].describe().to_string())

print(f"\nmean coverage by sector:")
print(df.groupby("sector")["coverage_pct"].mean().round(1).sort_values(ascending=False).to_string())

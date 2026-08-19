"""
WHAT THIS DOES
Produces companies_seed.csv -- the file meant to be loaded into this
project's `companies` DuckDB table. For every company in the universe, it
pulls their cached financial data (if fetched) and computes a 3-year
revenue growth rate (CAGR), using that to GUESS whether the company is
"High-Growth" or "Mature" (>=15% CAGR = High-Growth). Companies with no
cached data default to "Mature" with no signal attached.

IMPORTANT: this is a starting guess, not a verified answer. company_type
drives your entire pillar-weight vector downstream -- CAGR misfires on
things like COVID-recovery bounces and M&A-driven growth (see
docs/edgar_hardening.md for real examples that were caught this way). The
`type_signal` column exists so you can see what the guess was based on and
overrule it. Review before trusting.

EXAMPLE
Run: python 07_seed.py
- For AMZN: reads big_cache/AMZN.json, extracts 4+ years of revenue,
  computes CAGR (e.g. 8%), labels it "Mature" with signal "3yr rev CAGR 8%"
- Writes one row per company to companies_seed.csv
- Prints every company classified High-Growth, e.g.
  "AXON High-Growth Axon Enterprise (3yr rev CAGR 33%)"

OUTPUT
companies_seed.csv: ticker, name, sector, industry, company_type, cik,
type_signal -- for all 503 S&P 500 companies
"""
import csv
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "big_cache")

universe = json.load(open(os.path.join(HERE, "sp500_universe.json")))


def revenue_series(usgaap):
    tags = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
            "SalesRevenueNet", "RevenuesNetOfInterestExpense"]
    s = pd.Series(dtype=float)
    for tag in tags:
        if tag not in usgaap or "USD" not in usgaap[tag]["units"]:
            continue
        recs = []
        for p in usgaap[tag]["units"]["USD"]:
            if p.get("form") not in ("10-K", "10-K/A") or "start" not in p:
                continue
            if not (350 <= (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days <= 380):
                continue
            recs.append({"end": p["end"], "val": p["val"], "filed": p["filed"]})
        if recs:
            df = pd.DataFrame(recs).sort_values("filed").groupby("end").first()
            s = s.combine_first(df["val"])
    return s.sort_index()


def classify(tkr):
    """Return (company_type, signal_str) using 3yr revenue CAGR when data exists."""
    path = os.path.join(CACHE, f"{tkr}.json")
    if not os.path.exists(path):
        return "Mature", ""            # default; no data fetched
    usgaap = json.load(open(path))["facts"].get("us-gaap", {})
    rev = revenue_series(usgaap).dropna()
    if len(rev) < 4:
        return "Mature", "sparse"
    recent = rev.iloc[-4:]
    cagr = (recent.iloc[-1] / recent.iloc[0]) ** (1 / 3) - 1
    if cagr >= 0.15:
        return "High-Growth", f"3yr rev CAGR {cagr:.0%}"
    return "Mature", f"3yr rev CAGR {cagr:.0%}"


rows, hg = [], []
for c in universe:
    ctype, signal = classify(c["ticker"])
    rows.append({
        "ticker": c["ticker"], "name": c["name"], "sector": c["sector"],
        "industry": c["industry"], "company_type": ctype,
        "cik": c["cik"], "type_signal": signal,
    })
    if ctype == "High-Growth":
        hg.append((c["ticker"], c["name"], c["sector"], signal))

with open(os.path.join(HERE, "companies_seed.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"wrote companies_seed.csv: {len(rows)} companies")
print(f"classified High-Growth (>=15% 3yr rev CAGR): {len(hg)}")
for t, n, s, sig in sorted(hg, key=lambda x: x[2]):
    print(f"  {t:<6} {s:<12} {n}  ({sig})")

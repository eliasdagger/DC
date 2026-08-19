"""
WHAT THIS DOES
Builds the master list of all 503 S&P 500 companies with their sector,
sub-industry, and CIK -- the reference file (sp500_universe.json) that
every other script in this pipeline (06, 07, 09, 10, 11) reads from. Pulls
the constituent list from a public GitHub mirror of the S&P 500, cross-
checks each ticker's CIK against SEC's own list to catch mismatches, and
maps the official GICS sector names (e.g. "Information Technology") onto
the simpler internal buckets this project uses (e.g. "Technology").

EXAMPLE
Run: python 05_universe.py
- Downloads the S&P 500 constituent CSV, prints "S&P 500 constituents: 503"
- Prints a sector breakdown: "Technology 96", "Industrials 83", ...
- Prints any ticker where the CSV's listed CIK disagrees with SEC's current
  CIK for that ticker (a mismatch would be worth investigating)
- Writes sp500_universe.json

OUTPUT
sp500_universe.json: ticker, name, sector, industry, cik for all 503
companies. Everything downstream depends on this file existing first.
"""
import csv
import io
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HEADERS = {"User-Agent": "Dagher Capital dagher414@gmail.com"}


def get_text(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)).read().decode()


def get_json(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)))


# ── 1. S&P 500 constituents ──────────────────────────────────────────────────
csv_txt = get_text("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv")
rows = list(csv.DictReader(io.StringIO(csv_txt)))
print(f"S&P 500 constituents: {len(rows)}")

# ── 2. SEC's authoritative ticker->CIK (to catch mismatches) ─────────────────
sec = get_json("https://www.sec.gov/files/company_tickers.json")
sec_map = {r["ticker"]: r["cik_str"] for r in sec.values()}

# GICS sector -> our internal sector bucket
SECTOR_MAP = {
    "Information Technology": "Technology",
    "Communication Services": "Technology",
    "Consumer Discretionary": "Consumer",
    "Consumer Staples": "Consumer",
    "Financials": "Financials",
    "Real Estate": "REIT",
    "Industrials": "Industrials",
    "Energy": "Energy",
    "Health Care": "Healthcare",
    "Materials": "Materials",
    "Utilities": "Utilities",
}

out = []
mismatches = []
for r in rows:
    tkr = r["Symbol"].replace(".", "-")   # BRK.B -> BRK-B for SEC/yfinance
    gics = r["GICS Sector"]
    sec_cik = sec_map.get(tkr) or sec_map.get(r["Symbol"])
    listed_cik = int(r["CIK"]) if r["CIK"].isdigit() else None

    if sec_cik and listed_cik and sec_cik != listed_cik:
        mismatches.append((r["Symbol"], listed_cik, sec_cik))

    out.append({
        "ticker": tkr,
        "name": r["Security"],
        "sector": SECTOR_MAP.get(gics, gics),
        "gics_sector": gics,
        "industry": r["GICS Sub-Industry"],
        "cik": sec_cik or listed_cik,
        "company_type": "",     # filled in stage 06 with financial signals
    })

with open(os.path.join(HERE, "sp500_universe.json"), "w") as f:
    json.dump(out, f, indent=2)

# sector distribution
from collections import Counter
dist = Counter(o["sector"] for o in out)
print("\nsector distribution:")
for s, n in dist.most_common():
    print(f"  {s:<14} {n}")

print(f"\nCIK mismatches (S&P list vs SEC current): {len(mismatches)}")
for sym, listed, seccik in mismatches[:25]:
    print(f"  {sym:<6} list={listed:<10} sec={seccik}")

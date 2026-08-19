"""
WHAT THIS DOES
Same download pattern as 01_fetch.py, but pulls a much larger, stratified
sample -- 20 companies from each of 9 sectors (~160-180 companies) -- from
the full S&P 500 list built by 05_universe.py. Also flags "suspect"
companies whose fetched data has fewer than 150 accounting concepts, which
is the fingerprint of a ticker pointing at a thin/reorganized shell entity
(the Exxon problem: the ticker moved to a new CIK after a holding-company
reorg, and the new CIK has almost no filing history).

EXAMPLE
Run: python 06_fetch_big.py
- Reads sp500_universe.json, takes the first 20 tickers per sector
- Fetches each into big_cache/{ticker}.json
- AMZN's file has 545 concepts -> nothing printed, assumed fine
- XOM's file has only 94 concepts -> prints
  "XOM 94 concepts <-- SUSPECT (thin)" and logs it to cik_suspects.json

OUTPUT
big_cache/ folder: ~160-180 company JSON files
cik_suspects.json: list of thin/failed tickers to investigate
"""
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "big_cache")
HEADERS = {"User-Agent": "Dagher Capital dagher414@gmail.com"}

os.makedirs(CACHE, exist_ok=True)
universe = json.load(open(os.path.join(HERE, "sp500_universe.json")))

# stratified: cap per sector so no sector dominates, but cover all
PER_SECTOR = 20
from collections import defaultdict
buckets = defaultdict(list)
for c in universe:
    buckets[c["sector"]].append(c)
sample = []
for sector, cos in buckets.items():
    sample.extend(cos[:PER_SECTOR])
print(f"sampling {len(sample)} of {len(universe)} companies")

suspects = []
for i, c in enumerate(sample, 1):
    tkr, cik = c["ticker"], c["cik"]
    path = os.path.join(CACHE, f"{tkr}.json")
    if os.path.exists(path):
        continue
    if not cik:
        print(f"  [{i:>3}] {tkr:<6} NO CIK")
        continue
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as r:
            raw = r.read()
        d = json.loads(raw)
        n = len(d["facts"].get("us-gaap", {}))
        with open(path, "wb") as f:
            f.write(raw)
        if n < 150:                      # Exxon-style reorg signature
            suspects.append((tkr, cik, n))
            print(f"  [{i:>3}] {tkr:<6} {n:>4} concepts  <-- SUSPECT (thin)")
    except urllib.error.HTTPError as e:
        print(f"  [{i:>3}] {tkr:<6} HTTP {e.code}")
        suspects.append((tkr, cik, f"HTTP{e.code}"))
    except Exception as e:
        print(f"  [{i:>3}] {tkr:<6} ERR {e}")
    time.sleep(0.13)

json.dump(suspects, open(os.path.join(HERE, "cik_suspects.json"), "w"), indent=2)
print(f"\ndone. {len(suspects)} suspects flagged -> cik_suspects.json")

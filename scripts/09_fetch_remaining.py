"""
WHAT THIS DOES
Finishes what 06_fetch_big.py started -- fetches every S&P 500 ticker NOT
already sitting in big_cache/, so all 503 companies end up cached instead
of just the 160-180 company sample. Same thin-concept suspect-flagging
logic as 06_fetch_big.py.

EXAMPLE
Run: python 09_fetch_remaining.py
- Compares the full 503-ticker universe against what's already in
  big_cache/ (from running 06_fetch_big.py first)
- Fetches only the missing ~320-340 tickers
- Appends any new suspects to cik_suspects.json
- Prints progress every 25 tickers: "... AXON ok, 626 concepts"

OUTPUT
big_cache/ grows from ~160-180 files to (ideally) all 503
cik_suspects.json: updated with any new thin/failed tickers
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
have = {f[:-5] for f in os.listdir(CACHE) if f.endswith(".json")}
todo = [c for c in universe if c["ticker"] not in have]
print(f"{len(have)} cached, {len(todo)} remaining of {len(universe)}")

suspects = json.load(open(os.path.join(HERE, "cik_suspects.json"))) if os.path.exists(
    os.path.join(HERE, "cik_suspects.json")) else []

for i, c in enumerate(todo, 1):
    tkr, cik = c["ticker"], c["cik"]
    if not cik:
        print(f"  [{i:>3}/{len(todo)}] {tkr:<6} NO CIK")
        continue
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
        d = json.loads(raw)
        n = len(d["facts"].get("us-gaap", {}))
        with open(os.path.join(CACHE, f"{tkr}.json"), "wb") as f:
            f.write(raw)
        if n < 150:
            suspects.append([tkr, cik, n])
            print(f"  [{i:>3}/{len(todo)}] {tkr:<6} {n:>4} concepts  <-- SUSPECT (thin)")
        elif i % 25 == 0:
            print(f"  [{i:>3}/{len(todo)}] ... {tkr} ok, {n} concepts")
    except urllib.error.HTTPError as e:
        print(f"  [{i:>3}/{len(todo)}] {tkr:<6} HTTP {e.code}")
        suspects.append([tkr, cik, f"HTTP{e.code}"])
    except Exception as e:
        print(f"  [{i:>3}/{len(todo)}] {tkr:<6} ERR {e}")
        suspects.append([tkr, cik, f"ERR:{e}"])
    time.sleep(0.13)

json.dump(suspects, open(os.path.join(HERE, "cik_suspects.json"), "w"), indent=2)
print(f"\ndone. total suspects: {len(suspects)}")
print(f"total cached now: {len([f for f in os.listdir(CACHE) if f.endswith('.json')])}")

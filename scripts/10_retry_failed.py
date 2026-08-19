"""
WHAT THIS DOES
Cleanup pass. Some fetches in 09_fetch_remaining.py fail from transient
network errors (timeout, connection reset) rather than a real problem with
the ticker. This script finds whatever's still missing from big_cache/
after 09 finished, and retries each one individually with a longer
timeout -- separating "just needed another try" from "still genuinely
broken."

EXAMPLE
Run: python 10_retry_failed.py
- Prints "missing: ['APA', 'BLK', ...]" -- whatever's still absent
- Retries each ticker one at a time
- Success: "APA OK 720 concepts"
- Still broken: "APA STILL FAILING: <error message>"

OUTPUT
big_cache/: fills in whatever gaps remain
cik_suspects.json: updated to reflect what's still actually broken
"""
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "big_cache")
HEADERS = {"User-Agent": "Dagher Capital dagher414@gmail.com"}

universe = {c["ticker"]: c for c in json.load(open(os.path.join(HERE, "sp500_universe.json")))}
have = {f[:-5] for f in os.listdir(CACHE) if f.endswith(".json")}
missing = [t for t in universe if t not in have]
print(f"missing: {missing}")

suspects = json.load(open(os.path.join(HERE, "cik_suspects.json")))
suspects = [s for s in suspects if s[0] not in missing]   # drop the transient-error entries; re-add if still bad

for tkr in missing:
    cik = universe[tkr]["cik"]
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
        d = json.loads(raw)
        n = len(d["facts"].get("us-gaap", {}))
        with open(os.path.join(CACHE, f"{tkr}.json"), "wb") as f:
            f.write(raw)
        print(f"  {tkr:<6} OK  {n} concepts")
        if n < 150:
            suspects.append([tkr, cik, n])
    except Exception as e:
        print(f"  {tkr:<6} STILL FAILING: {e}")
        suspects.append([tkr, cik, f"ERR:{e}"])
    time.sleep(0.2)

json.dump(suspects, open(os.path.join(HERE, "cik_suspects.json"), "w"), indent=2)
print(f"\ntotal cached: {len([f for f in os.listdir(CACHE) if f.endswith('.json')])}")
print(f"total suspects: {len(suspects)}")

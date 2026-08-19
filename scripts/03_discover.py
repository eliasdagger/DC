"""Stage 3: for companies missing a field, find what tags they DO report that fit."""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "edgar_cache")


def annual_count(body, kind):
    units = body["units"]
    key = next((k for k in ("USD", "shares") if k in units), None)
    if key is None:
        return 0, "", ""
    ends = []
    for p in units[key]:
        if p.get("form") not in ("10-K", "10-K/A"):
            continue
        if p["end"][:4] < "2010":
            continue
        if kind == "duration":
            if "start" not in p:
                continue
            days = (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days
            if not (350 <= days <= 380):
                continue
        else:
            if "start" in p:
                continue
        ends.append(p["end"])
    ends = sorted(set(ends))
    return len(ends), (ends[0][:4] if ends else ""), (ends[-1][:4] if ends else "")


def search(tickers, keywords, kind, exclude=()):
    for tk in tickers:
        path = os.path.join(CACHE, f"{tk}.json")
        if not os.path.exists(path):
            continue
        with open(path) as f:
            usgaap = json.load(f)["facts"].get("us-gaap", {})

        hits = []
        for tag, body in usgaap.items():
            low = tag.lower()
            if not any(k.lower() in low for k in keywords):
                continue
            if any(x.lower() in low for x in exclude):
                continue
            n, first, last = annual_count(body, kind)
            if n >= 8:                       # only tags with real history
                hits.append((n, tag, first, last))

        hits.sort(reverse=True)
        print(f"\n  {tk}:")
        for n, tag, first, last in hits[:6]:
            print(f"      {n:>3} yrs  {first}-{last}  {tag}")


if __name__ == "__main__":
    QUERIES = [
        ("dep_amort  -> tech misses", ["MSFT", "GOOGL", "ORCL"],
         ["depreciation", "amortization"], "duration", ["accumulated", "pershare", "intangibleassetsnet"]),

        ("capex -> banks + utility", ["JPM", "BAC", "NEE"],
         ["paymentstoacquire", "capitalexpend"], "duration", []),

        ("dividends_paid -> healthcare", ["JNJ", "PFE"],
         ["dividend"], "duration", ["pershare", "declared", "rate"]),

        ("debt_repaid -> misses", ["MSFT", "CAT", "GS"],
         ["repayment"], "duration", []),

        ("cogs -> non-retail", ["MCD", "UNP", "NEE"],
         ["cost"], "duration", ["pershare", "issuance"]),

        ("total_liabilities -> spotty", ["AAPL", "MSFT", "VZ"],
         ["liabilities"], "instant", ["current", "deferred", "accrued", "other", "operatinglease"]),
    ]
    for title, tickers, kws, kind, excl in QUERIES:
        print(f"\n{'='*78}\n{title}   [{kind}]\n{'='*78}")
        search(tickers, kws, kind, excl)

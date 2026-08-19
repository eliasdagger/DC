"""Run the existing tag map across big_cache; find (field, company) misses and
discover what those companies report instead. Output: gap report + new candidates."""
import json
import os
from collections import defaultdict

import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "big_cache")
PROJ = os.path.join("C:", os.sep, "Users", "elied", "Projects", "DC", "DC")

tagmap = yaml.safe_load(open(os.path.join(PROJ, "configs/xbrl_tags.yaml")))
universe = {c["ticker"]: c for c in json.load(open(os.path.join(HERE, "sp500_universe.json")))}

# combine fields + helpers into one {field: (kind, [tags])}
ALL = {}
for f, spec in tagmap["fields"].items():
    ALL[f] = (spec["kind"], spec["tags"])


def annual_count(usgaap, tag, kind):
    if tag not in usgaap:
        return 0
    units = usgaap[tag]["units"]
    key = next((k for k in ("USD", "shares") if k in units), None)
    if not key:
        return 0
    ends = set()
    for p in units[key]:
        if p.get("form") not in ("10-K", "10-K/A") or p["end"][:4] < "2010":
            continue
        if kind == "duration":
            if "start" not in p:
                continue
            if not (350 <= (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days <= 380):
                continue
        elif "start" in p:
            continue
        ends.add(p["end"])
    return len(ends)


def coverage(usgaap, field):
    kind, tags = ALL[field]
    return max((annual_count(usgaap, t, kind) for t in tags), default=0)


files = [f for f in os.listdir(CACHE) if f.endswith(".json")]
print(f"analyzing {len(files)} companies against current tag map\n")

# fields that legitimately don't apply per sector (from sector_applicability.md)
SECTOR_EXEMPT = {
    "Financials": {"cogs", "current_assets", "current_liabilities"},
    "REIT": {"cogs"},
}

gaps = defaultdict(list)          # field -> [(ticker, sector)]
for fn in files:
    tkr = fn[:-5]
    sector = universe.get(tkr, {}).get("sector", "?")
    usgaap = json.load(open(os.path.join(CACHE, fn)))["facts"].get("us-gaap", {})
    for field in ALL:
        if field in SECTOR_EXEMPT.get(sector, set()):
            continue
        if coverage(usgaap, field) < 5:      # under 5 annual periods = real gap
            gaps[field].append((tkr, sector))

print("FIELDS WITH GAPS (excluding known sector exemptions):\n")
for field in sorted(gaps, key=lambda f: -len(gaps[f])):
    hits = gaps[field]
    bysec = defaultdict(int)
    for _, s in hits:
        bysec[s] += 1
    secstr = ", ".join(f"{s}:{n}" for s, n in sorted(bysec.items(), key=lambda x: -x[1]))
    sample = ", ".join(t for t, _ in hits[:6])
    print(f"  {field:<22} {len(hits):>3} companies   [{secstr}]")
    print(f"  {'':<22}     e.g. {sample}")

json.dump({f: v for f, v in gaps.items()}, open(os.path.join(HERE, "gaps.json"), "w"), indent=2)


# ── discovery: for the worst gaps, what DO these companies report? ──
def discover(tickers, keywords, kind, exclude=()):
    tagcount = defaultdict(int)
    for tkr in tickers:
        p = os.path.join(CACHE, f"{tkr}.json")
        if not os.path.exists(p):
            continue
        usgaap = json.load(open(p))["facts"].get("us-gaap", {})
        for tag in usgaap:
            low = tag.lower()
            if any(k in low for k in keywords) and not any(x in low for x in exclude):
                if annual_count(usgaap, tag, kind) >= 8:
                    tagcount[tag] += 1
    return sorted(tagcount.items(), key=lambda x: -x[1])


print("\n\nDISCOVERY on the largest gaps:\n")
DISCOVER = [
    ("total_debt", ["debt", "borrowings", "notespayable"], "instant",
     ["current", "issuancecost", "fairvalue", "netofdiscount", "weighted"]),
    ("preferred_equity", ["preferredstock"], "instant", ["shares", "dividend", "conversion"]),
    ("interest_expense", ["interest"], "duration",
     ["income", "receivable", "payable", "rate", "pershare", "capitalized"]),
]
for field, kws, kind, excl in DISCOVER:
    tickers = [t for t, _ in gaps.get(field, [])]
    if not tickers:
        print(f"  {field}: no gaps")
        continue
    print(f"  {field} ({len(tickers)} gap companies) — tags they report >=8yrs:")
    for tag, n in discover(tickers, kws, kind, excl)[:8]:
        cur = "  (in map)" if any(tag in tags for _, tags in [ALL[field]]) else ""
        print(f"      {n:>3} companies  {tag}{cur}")
    print()

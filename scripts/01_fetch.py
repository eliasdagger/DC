"""
WHAT THIS DOES
Downloads the full financial filing data for the companies in UNIVERSE (companyfacts JSON) from SEC EDGAR for a test on 32 companies, and
caches a JSON file per ticker to disk dumping its data. Also builds and saves the
ticker->CIK lookup table every other script in this pipeline reads from to identify a ticker and its 10 digit identification number.

EXAMPLE
Run: python 01_fetch.py
- Create a path to DC/scripts/edgar_cache
- Access the SEC's EDGAR API, each ticker is identified with a cik, here we get each ticker and their cik. Create our own dict of ticker:cik
- Write our lookup data in a json file, location: DC/scripts/_ticker_cik.json
- For group in UNIVERSE, we will check their tickers, for ticker in UNIVERSE, add into our 1D list
- For each ticker, build the path for their own data in CACHE/tk.json (DC/scripts/edgar_cache/tk.json)
- Writes edgar_cache/ticker_cik.json
  (10,000+ ticker -> CIK pairs)
- For the 32 ticker universe, fetch
  https://data.sec.gov/api/xbrl/companyfacts/CIK{...}.json and saves it to
  edgar_cache/AAPL.json, edgar_cache/MSFT.json, etc.
- Skips a ticker if its file already exists safe to re-run, won't
  re-download what you already have.
- Sleeps 0.15s between requests to stay under SEC's rate limit.

OUTPUT
edgar_cache/ folder: ~32 company JSON files + ticker_cik.json
"""
import json
import os
import time
import urllib.request

# Identification for SEC, else the US will block me
HEADERS = {"User-Agent": "Dagher Capital dagher414@gmail.com"}

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edgar_cache")

UNIVERSE = {
    "Technology":        ["AAPL", "MSFT", "NVDA", "GOOGL", "ORCL"],
    "Consumer":          ["AMZN", "WMT", "COST", "HD", "MCD"],
    "Financials":        ["JPM", "BAC", "WFC", "GS", "AXP"],
    "REIT":              ["AMT", "PLD", "SPG", "O", "EQIX"],
    "Industrials":       ["CAT", "BA", "HON", "UNP"],
    "Energy":            ["XOM", "CVX", "COP"],
    "Healthcare":        ["JNJ", "UNH", "PFE"],
    "Utilities/Telecom": ["NEE", "VZ"],
}


def get_url(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request) as r:
        # r: json -> dict
        return json.load(r)


def main():
    os.makedirs(CACHE, exist_ok=True)

    tickers = get_url("https://www.sec.gov/files/company_tickers.json")
    lookup = {row["ticker"]: row["cik_str"] for row in tickers.values()}

    with open(os.path.join(CACHE, "ticker_cik.json"), "w") as f:
        json.dump(lookup, f)
    print(f"ticker & cik dict: {len(lookup)} total entries")

    uni_tickers = [tckr for sector in UNIVERSE.values() for tckr in sector]
    print(f"Fetched {len(uni_tickers)} tickers from universe")

    for i, tckr in enumerate(uni_tickers, 1):
        path = os.path.join(CACHE, f"{tckr}.json")
        if os.path.exists(path):
            print(f"    [{i:>2}/{len(uni_tickers)}] {tckr:<6} cached")
            continue

        cik = lookup.get(tckr)
        if cik is None:
            print(f"    [{i:<2}/{len(uni_tickers)}] {tckr:<6} Error: Not Found")

        company_facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
        try:
            request = urllib.request.Request(company_facts_url, headers=HEADERS)
            with urllib.request.urlopen(request) as r:
                raw = r.read()

            with open(path, "wb") as f:
                f.write(raw)

            n = len(json.loads(raw)["facts"].get('us-gaap', {}))
            print(f"[{tckr:<6}] Concepts written: {n:>4} totalling {len(raw)/1e6:>5.1f} MB")
        except Exception as e:
            print(f"[{tckr:<6}] Exception {e} caught.")

        time.sleep(0.15)

if __name__ == "__main__":
    main()

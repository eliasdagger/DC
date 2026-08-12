import json
import urllib.request
import pandas as pd
"""EDGAR API rough n tough work"""

HEADERS = {"User-Agent": "DC dagher414@gmail.com"}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.load(r)

# def create_tickers_cik_table(conn.dd.DuckDBPyConnection) -> None:
#     conn.execute("""
#             CREATE TABLE tickers_cik(
#             ticker VARCHAR, 
#             cik VARCHAR
#             )
#         """)



# def tickers_cik_to_DuckDB(conn: dd.DuckDBPyConnection) -> 

# Identify cik with company ticker
def get_ticker_fundementals_XBRL(wanted_tckr: str) -> str:
    tickers = get("https://www.sec.gov/files/company_tickers.json")
    print("Tickers successfully attained.")
    cik = None

    for row in tickers.values():
        if row["ticker"] == wanted_tckr:
            cik = row["cik_str"]
            name = row["title"]
            break

    print(f"Found {wanted_tckr}'s name: {name} and cik: {cik}")

    paddedcik = str(cik).zfill(10)

    facts = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{paddedcik}.json")
    usgaap = facts["facts"]["us-gaap"]

    # naming bs
    """
    Once we accessed usgaap, we can find revenues or revenuefrom..blah..., then create a list of annual fiscal reports by matching if fp (fiscal period) is FY (full year)
    and form is 10-K which is an annual letter rather than 10-Q which is quarterly. fp couldve == Q1, Q2 etc...
    """
    concept = "Revenues" if "Revenues" in usgaap else "RevenueFromContractWithCustomerExcludingAssessedTax"
    units = usgaap[concept]["units"]["USD"]
    annual = [u for u in units if u.get("fp") == "FY" and u.get("form") == "10-K"]

    # Print the last 4yrs since the files are ascending
    for u in annual[-4:]:
        print(f"   {u['end']:<12} {u['filed']:<12} {u['val']:>18,}  {u['form']}")

    # create a dict of the keys which represent our terminology, then the values that match their terminology
    wanted = {
        "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
        "cogs": ["CostOfRevenue", "CostOfGoodsAndServicesSold"],
        "gross_profit": ["GrossProfit"],
        "net_income": ["NetIncomeLoss"],
        "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
        "total_assets": ["Assets"],
        "total_liabilities": ["Liabilities"],
        "current_assets": ["AssetsCurrent"],
        "current_liabilities": ["LiabilitiesCurrent"],
        "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
        "cash": ["CashAndCashEquivalentsAtCarryingValue"],
        "interest_expense": ["InterestExpense", "InterestExpenseNonoperating"],
    }

    print("Matching FundementalsRaw -> XBRL tags")

    for ours, theirs in wanted.items():
        match = next((c for c in theirs if c in usgaap), None)
        filler = "MATCH " if match else "MISS "
        print(f"    [{filler}] {ours:<22} {match or '  (none of: ' + ', '.join(theirs) + ')'}")

    

print(get_ticker_fundementals_XBRL("AMZN"))


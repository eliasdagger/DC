"""Stage 2: test candidate tags per field per company, measure REAL coverage."""

"""
Module: Access to Fundemental Data via SEC's EDGAR API  

Problem:
After pulling and dumping an entires companies 10k filings in 01_fetch.py, we have a lot of information which, to us, is useless with no benefit to our constructing our algorithm.
Also, when in pursuit to find a companies field / fundemental metric (Liabilites or Revenue), due to the percision of accounting practices, many companies will file their 
revenue denoted as "RevenueFromContractWithCustomerExcludingAssessedTax". There are many variations we are met with with do not match the simple naming conventions 
people often use. In addition, a company may not even make revenue.  
Description:
Reads companies cached fundemental data, identifies which fields are present in the companies filing. Saves coverage_raw storing company fundemental naming
convention the tags from the EDGAR filings use.  
Key Functions:
- main:
- append_company: Stores a company in DuckDB, but only if something actually changed
- get_company_attributes: Returns a company's attributes as they stood on a given date

Dependencies:
- pandas: For data handling
- duckdb: For caching

Example:
    >>> create_company_attributes_table(conn)
    >>> append_company(conn, Company(ticker='AMZN', name='Amazon', sector='Consumer',
    ...                              industry='Retail', company_type='Early-Stage'))
    >>> get_company_attributes(conn, 'AMZN')                  # current
    >>> get_company_attributes(conn, 'AMZN', '2024-06-01')    # as it stood then
"""
import json
import os
from collections import defaultdict

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "edgar_cache")

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

# kind: "duration" = measured over a period (has start); "instant" = point in time
FIELDS = {
    "revenue": ("duration", [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
        "RevenuesNetOfInterestExpense",
        "InterestAndDividendIncomeOperating",
    ]),
    "cogs": ("duration", [
        "CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold",
        "CostOfServices", "CostOfGoodsSoldExcludingDepreciationDepletionAndAmortization",
    ]),
    "gross_profit": ("duration", ["GrossProfit"]),
    "ebit": ("duration", [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ]),
    "dep_amort": ("duration", [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization",
        "DepreciationDepletionAndAmortizationExcludingAmortizationOfDeferredFinancingCosts",
    ]),
    "net_income": ("duration", [
        "NetIncomeLoss", "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ]),
    "cfo": ("duration", [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ]),
    "capex": ("duration", [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsForCapitalImprovements",
        "PaymentsToAcquireRealEstate",
        "PaymentsToAcquireOilAndGasProperty",
    ]),
    "interest_expense": ("duration", [
        "InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt",
        "InterestIncomeExpenseNet", "InterestExpenseBorrowings",
    ]),
    "dividends_paid": ("duration", [
        "PaymentsOfDividendsCommonStock", "PaymentsOfDividends",
        "PaymentsOfDistributionsToAffiliates",
    ]),
    "buybacks": ("duration", [
        "PaymentsForRepurchaseOfCommonStock", "PaymentsForRepurchaseOfEquity",
    ]),
    "debt_repaid": ("duration", [
        "RepaymentsOfLongTermDebt", "RepaymentsOfDebt",
        "RepaymentsOfLongTermDebtAndCapitalSecurities", "RepaymentsOfSeniorDebt",
    ]),
    # ── instant / balance sheet ──
    "total_assets": ("instant", ["Assets"]),
    "total_liabilities": ("instant", ["Liabilities"]),
    "equity": ("instant", [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ]),
    "current_assets": ("instant", ["AssetsCurrent"]),
    "current_liabilities": ("instant", ["LiabilitiesCurrent"]),
    "retained_earnings": ("instant", ["RetainedEarningsAccumulatedDeficit"]),
    "cash": ("instant", [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndDueFromBanks",
    ]),
    "total_debt": ("instant", [
        "LongTermDebt", "LongTermDebtNoncurrent",
        "DebtLongtermAndShorttermCombinedAmount", "LongTermDebtAndCapitalLeaseObligations",
    ]),
    "preferred_equity": ("instant", [
        "PreferredStockValue", "PreferredStockLiquidationPreferenceValue",
    ]),
    "shares_outstanding": ("instant", [
        "CommonStockSharesOutstanding", "CommonStockSharesIssued",
    ]),
}

MIN_YEAR = 2010


def annual_points(usgaap, tag, kind):
    """Return {fiscal_year_end: value} for genuine ANNUAL figures."""
    if tag not in usgaap:
        return {}
    units = usgaap[tag]["units"]
    key = next((k for k in ("USD", "shares", "USD/shares") if k in units), None)
    if key is None:
        return {}

    out = {}
    for p in units[key]:
        if p.get("form") not in ("10-K", "10-K/A"):
            continue
        if p["end"][:4] < str(MIN_YEAR):
            continue
        if kind == "duration":
            if "start" not in p:
                continue
            days = (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days
            if not (350 <= days <= 380):        # reject quarters
                continue
        else:
            if "start" in p:                     # instants have no start
                continue
        out.setdefault(p["end"], p["val"])
    return out


def main():
    rows = []
    tag_usage = defaultdict(int)

    for sector, tickers in UNIVERSE.items():
        for tk in tickers:
            path = os.path.join(CACHE, f"{tk}.json")
            if not os.path.exists(path):
                continue
            with open(path) as f:
                usgaap = json.load(f)["facts"].get("us-gaap", {})

            for field, (kind, candidates) in FIELDS.items():
                merged, winners = {}, []
                for tag in candidates:
                    pts = annual_points(usgaap, tag, kind)
                    if pts:
                        winners.append(tag)
                        tag_usage[(field, tag)] += 1
                    for k, v in pts.items():
                        merged.setdefault(k, v)      # first candidate wins per period

                years = sorted(merged)
                rows.append({
                    "sector": sector, "ticker": tk, "field": field, "kind": kind,
                    "years": len(years),
                    "first": years[0][:4] if years else "",
                    "last": years[-1][:4] if years else "",
                    "tags_hit": len(winners),
                    "winner": winners[0] if winners else "",
                })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(HERE, "coverage_raw.csv"), index=False)

    # ── coverage matrix: mean annual periods per sector ──
    pivot = df.pivot_table(index="field", columns="sector", values="years", aggfunc="mean").round(1)
    order = [f for f in FIELDS]
    pivot = pivot.reindex(order)
    print("MEAN ANNUAL PERIODS AVAILABLE (2010+), by sector\n")
    print(pivot.to_string())

    print("\n\nFIELDS WITH ZERO COVERAGE somewhere:\n")
    zero = df[df["years"] == 0].groupby(["field", "sector"])["ticker"].apply(list)
    for (field, sector), tks in zero.items():
        print(f"  {field:<20} {sector:<18} {', '.join(tks)}")

    tu = pd.DataFrame(
        [{"field": f, "tag": t, "companies": n} for (f, t), n in tag_usage.items()]
    ).sort_values(["field", "companies"], ascending=[True, False])
    tu.to_csv(os.path.join(HERE, "tag_usage.csv"), index=False)


if __name__ == "__main__":
    main()

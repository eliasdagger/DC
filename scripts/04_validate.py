"""Stage 4: validate the final tag map (candidates + derivations) across all sectors."""
import json
import os

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

TAGS = {
    "revenue": ("duration", [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet", "SalesRevenueServicesNet",
        "RevenuesNetOfInterestExpense", "InterestAndDividendIncomeOperating",
    ]),
    "cogs": ("duration", [
        "CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold", "CostOfServices",
        "CostOfGoodsSoldExcludingDepreciationDepletionAndAmortization",
    ]),
    "gross_profit_tag": ("duration", ["GrossProfit"]),
    "ebit": ("duration", [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ]),
    "dep_amort_combined": ("duration", [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization",
    ]),
    "depreciation_only": ("duration", ["Depreciation"]),
    "amortization_only": ("duration", ["AmortizationOfIntangibleAssets"]),
    "net_income": ("duration", ["NetIncomeLoss", "ProfitLoss"]),
    "cfo": ("duration", [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ]),
    "capex": ("duration", [
        "PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets",
        "PaymentsForCapitalImprovements", "PaymentsToAcquireRealEstate",
        "PaymentsToAcquireOilAndGasProperty",
    ]),
    "interest_expense": ("duration", [
        "InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt",
        "InterestIncomeExpenseNet", "InterestExpenseBorrowings",
    ]),
    "dividends_paid": ("duration", [
        "PaymentsOfDividendsCommonStock", "PaymentsOfOrdinaryDividends",
        "DividendsCommonStockCash", "PaymentsOfDividends",
    ]),
    "buybacks": ("duration", [
        "PaymentsForRepurchaseOfCommonStock", "PaymentsForRepurchaseOfEquity",
        "TreasuryStockValueAcquiredCostMethod",
    ]),
    "debt_repaid": ("duration", [
        "RepaymentsOfLongTermDebt", "RepaymentsOfDebt",
        "RepaymentsOfDebtMaturingInMoreThanThreeMonths",
        "RepaymentsOfLongTermDebtAndCapitalSecurities", "RepaymentsOfSeniorDebt",
    ]),
    "total_assets": ("instant", ["Assets"]),
    "total_liabilities_tag": ("instant", ["Liabilities"]),
    "liabilities_and_equity": ("instant", ["LiabilitiesAndStockholdersEquity"]),
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
    "preferred_equity": ("instant", ["PreferredStockValue"]),
    "shares_outstanding": ("instant", ["CommonStockSharesOutstanding", "CommonStockSharesIssued"]),
}


def series(usgaap, tag, kind):
    if tag not in usgaap:
        return pd.Series(dtype=float)
    units = usgaap[tag]["units"]
    key = next((k for k in ("USD", "shares") if k in units), None)
    if key is None:
        return pd.Series(dtype=float)
    recs = []
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
        recs.append({"end": p["end"], "val": p["val"], "filed": p["filed"]})
    if not recs:
        return pd.Series(dtype=float)
    df = pd.DataFrame(recs).sort_values("filed").groupby("end").first()
    return df["val"]


def coalesce(usgaap, field):
    kind, cands = TAGS[field]
    out = pd.Series(dtype=float)
    for tag in cands:
        out = out.combine_first(series(usgaap, tag, kind))
    return out


def build(usgaap):
    f = {k: coalesce(usgaap, k) for k in TAGS}

    # ── derivations ──
    f["gross_profit"] = f["gross_profit_tag"].combine_first(f["revenue"] - f["cogs"])
    f["total_liabilities"] = (
        f["total_liabilities_tag"]
        .combine_first(f["liabilities_and_equity"] - f["equity"])
        .combine_first(f["total_assets"] - f["equity"])
    )
    f["dep_amort"] = f["dep_amort_combined"].combine_first(
        f["depreciation_only"].add(f["amortization_only"], fill_value=0)
    )
    f["ebitda"] = f["ebit"] + f["dep_amort"]
    f["working_capital"] = f["current_assets"] - f["current_liabilities"]
    f["fcf"] = f["cfo"] - f["capex"]
    return f


REPORT = ["revenue", "cogs", "gross_profit", "ebit", "ebitda", "dep_amort", "net_income",
          "cfo", "capex", "fcf", "interest_expense", "dividends_paid", "buybacks",
          "debt_repaid", "total_assets", "total_liabilities", "equity", "current_assets",
          "current_liabilities", "working_capital", "retained_earnings", "cash",
          "total_debt", "preferred_equity", "shares_outstanding"]

rows = []
for sector, tickers in UNIVERSE.items():
    for tk in tickers:
        p = os.path.join(CACHE, f"{tk}.json")
        if not os.path.exists(p):
            continue
        with open(p) as fh:
            usgaap = json.load(fh)["facts"].get("us-gaap", {})
        built = build(usgaap)
        for field in REPORT:
            s = built[field].dropna()
            rows.append({"sector": sector, "ticker": tk, "field": field, "years": len(s)})

df = pd.DataFrame(rows)
pivot = df.pivot_table(index="field", columns="sector", values="years", aggfunc="mean").round(1)
pivot = pivot.reindex(REPORT)
print("AFTER FIXES — mean annual periods (2010+), by sector\n")
print(pivot.to_string())
df.to_csv(os.path.join(HERE, "coverage_final.csv"), index=False)

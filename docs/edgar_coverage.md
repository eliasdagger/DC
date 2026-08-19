# EDGAR Tag Coverage Study

What this is: an empirical test of which `us-gaap` tags actually contain data, run across 32 companies in 8 sectors. It exists because *a tag existing is not the same as a tag having data*, and the difference silently produces empty columns.

**Universe** — 32 companies, annual figures (10-K), 2010 onward:

| Sector | Companies |
|---|---|
| Technology | AAPL, MSFT, NVDA, GOOGL, ORCL |
| Consumer | AMZN, WMT, COST, HD, MCD |
| Financials | JPM, BAC, WFC, GS, AXP |
| REIT | AMT, PLD, SPG, O, EQIX |
| Industrials | CAT, BA, HON, UNP |
| Energy | XOM, CVX, COP |
| Healthcare | JNJ, UNH, PFE |
| Utilities/Telecom | NEE, VZ |

Output config: [`configs/xbrl_tags.yaml`](../configs/xbrl_tags.yaml)

---

## Three traps, found the hard way

### 1. Existence ≠ coverage

The obvious check — `if tag in usgaap` — passes for tags that hold almost nothing.

`GrossProfit` exists in Amazon's filings. It has **3 annual data points, ending 2009**. Amazon stopped presenting a gross profit line. A pipeline built on the existence check produces a column that's 3/17 full and looks like a bug in your loader.

**Always measure the number of periods and the date span, not just presence.**

### 2. `fp="FY"` does not mean annual

A 10-K contains quarterly breakdowns. Those records can carry `fp="FY"` and `form="10-K"` while holding a *quarterly* value.

Real example, Amazon FY2017 revenue:

```
tag: RevenueFromContractWithCustomer...   60,453,000,000    ← Q4 only
tag: SalesRevenueNet                     177,866,000,000    ← the real FY figure
```

Both records passed `fp=="FY" and form=="10-K"`. Using the first would understate revenue by 66% and corrupt every margin, growth, and valuation metric downstream.

**The fix** — for duration concepts, check the actual span:

```python
days = (pd.Timestamp(p["end"]) - pd.Timestamp(p["start"])).days
if not (350 <= days <= 380):
    continue
```

Instant concepts (balance sheet items) have no `start` at all — reject any record that has one. This duration/instant split is why every field in the config carries a `kind`.

### 3. Tickers can point at the wrong CIK

`company_tickers.json` maps a ticker to whichever entity **currently** holds it. After a holding-company reorganization, the ticker moves to the new entity while all history stays under the old CIK.

Exxon, live today:

| CIK | Entity | Concepts | Revenue history |
|---|---|---|---|
| 2115436 | ExxonMobil Holdings Corp | 94 | **0 years** ← what the map returns |
| 34088 | EXXON MOBIL CORP | 438 | **17 years** ← where the data is |

Nothing errors. You just silently get an almost-empty company. In the first pass of this study, Exxon dragged the entire Energy sector's averages down and looked like an Energy-sector problem rather than one broken lookup.

**Detection:** after fetching, check concept count and history length. Under ~150 concepts, or under 5 years for an established company, means look for a predecessor CIK. Overrides live in the `cik_overrides` block of the config.

---

## Before and after

Mean annual periods available per field, 2010+ (max ≈ 16).

**Fields the fixes repaired:**

| Field | Fix | Before → After |
|---|---|---|
| `total_liabilities` | derive from `LiabilitiesAndStockholdersEquity − equity` | Consumer 6.6 → **16.4**<br>Utilities 3.5 → **16.0**<br>Technology 11.2 → **15.8** |
| `dep_amort` | sum `Depreciation` + `AmortizationOfIntangibleAssets` | Technology 6.6 → **14.4** |
| `dividends_paid` | add `PaymentsOfOrdinaryDividends` | Healthcare 5.3 → **16.3** |
| `gross_profit` | derive `revenue − cogs` | Consumer 3.6 → **13.2**<br>Technology 10.8 → **14.4** |
| all Energy fields | CIK override | ~10 → **~16** |

`total_liabilities` is worth noting: the derivation is an accounting identity, so the derived value is **exact**, not an estimate. The balance sheet must balance.

`ebitda` only became computable at all once `dep_amort` was repaired — it now reaches 14-16 periods in every sector.

---

## Final coverage

```
field                Consumer  Energy  Financials  Healthcare  Industrials  REIT  Tech  Util/Tel
revenue                  16.4    16.0        15.8        16.3         16.0  14.0  16.0      13.5
cogs                     13.2     6.7         0.0        16.3         12.0   5.2  14.4       4.0
gross_profit             13.2     6.7         0.0        16.3         12.0   5.2  14.4       4.0
ebit                     16.4    14.3        16.0        16.3         16.0  14.2  16.0      16.0
ebitda                   16.4    14.3        16.0        16.3         16.0  14.2  14.4      16.0
net_income               16.4    16.0        16.0        16.3         16.0  16.0  16.0      16.0
cfo                      16.4    16.0        16.0        16.3         16.0  16.0  16.0      16.0
capex                    16.4    14.3         6.2        16.3         16.0  15.0  14.2       4.5
fcf                      16.4    14.3         6.2        16.3         16.0  15.0  14.2       4.5
total_assets             16.4    16.0        16.0        16.3         16.0  16.0  15.8      16.0
total_liabilities        16.4    16.0        16.0        16.3         16.0  16.0  15.8      16.0
equity                   16.4    16.0        16.0        16.3         17.0  16.0  16.2      16.0
current_assets           16.4    16.0         0.0        16.3         16.0   6.4  15.8      16.0
current_liabilities      16.4    16.0         0.0        16.3         16.0   6.4  15.8      16.0
working_capital          16.4    16.0         0.0        16.3         16.0   6.4  15.8      16.0
retained_earnings        16.4    16.0        16.0        17.0         16.5  13.2  15.6      17.0
cash                     16.6    16.0        16.0        16.3         14.8  15.6  16.2      16.0
total_debt               16.4    16.0        13.6        16.3         16.0  12.8  13.8      16.0
preferred_equity          8.8     5.3         9.0        15.7          0.0   8.6   3.4       5.0
shares_outstanding       13.6    16.0        16.0        16.3         16.0  13.4  16.0      16.0
```

---

## What remains zero — and can't be fixed

These are not gaps in the tag map. They are structural facts about how those businesses report, and no additional candidate tag will resolve them.

**Financials: `cogs`, `gross_profit`, `current_assets`, `current_liabilities`, `working_capital` — all 0.0 across all five banks.**

Banks file *unclassified* balance sheets. There is no current/non-current split because the distinction is meaningless when your inventory is money. And there is no cost of goods because they don't sell goods.

**REITs: `current_assets` / `current_liabilities` at 6.4/16** — same unclassified balance sheet, applied inconsistently across the sector.

**Financials `capex` at 6.2** — banks have `PaymentsToAcquire*` tags, but they refer to securities purchases, not property and equipment. Substituting them would put a completely different quantity into the field. Left empty on purpose.

### The consequence for screening

Altman Z's first component is `working_capital / total_assets`.

Working capital is **unavailable for every bank tested**. So the Altman Z-score cannot be computed for Financials at all — not poorly, not approximately. The input does not exist.

This confirms what the sector-neutrality discussion anticipated: ranking a bank *within* its sector doesn't rescue a metric whose inputs were never filed. See [`sector_applicability.md`](sector_applicability.md).

---

## One field with different semantics

`preferred_equity` scores low everywhere (3.4-15.7), but that's not missing data — **most companies have no preferred stock**, so there's nothing to tag.

This is the one field where treating absence as `0.0` is correct rather than dangerous. Everywhere else, missing means unknown, and substituting zero would drag a healthy company toward false distress.

---

## Reproducing

Scripts used, in order:

1. `01_fetch.py` — fetch and cache companyfacts for the universe
2. `02_analyze.py` — test seed candidates, measure real coverage
3. `03_discover.py` — for gaps, search what those companies *do* report
4. `04_validate.py` — apply the final map plus derivations, re-measure

The discovery step is the one to repeat when adding a sector. Point it at a company that fails, search by keyword, and read what comes back with real history attached.

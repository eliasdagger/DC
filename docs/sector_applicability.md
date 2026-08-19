# Sector Metric Applicability

A spec for which of the 41 metrics in `QuantFundamentalData` mean anything for which sectors, what substitutes where they don't, and how the composite score renormalizes when metrics drop out.

This resolves the open question from the Layer 2 plan: *sector exclusion was handled for Altman Z but never carried through to ranking.*

---

## The core principle

**Sector-neutral ranking does not fix an invalid metric.**

It's tempting to think `groupby(sector).rank(pct=True)` solves everything. It doesn't, and the distinction matters:

| Situation | Ranking within sector fixes it? |
|---|---|
| Metric is **distorted** by sector — utilities carry more debt than software, but debt/equity is a real, comparable number | **Yes.** Rank within sector and the comparison is fair. |
| Metric is **meaningless** for the sector — a bank's enterprise value, where debt is raw material rather than financing | **No.** Ranking nonsense against nonsense returns a confident-looking percentile built on nothing. |
| Metric is **unavailable** — banks file no `working_capital` | **No.** There is nothing to rank. |

So each metric needs an *applicability set*: the sectors where it carries signal. Outside that set it is excluded, and the composite renormalizes over what's left.

Two separate reasons for exclusion, worth tracking separately because they have different lifespans:

- **INVALID** — the metric is conceptually wrong here. Permanent. No data source fixes it.
- **UNAVAILABLE** — not filed. Might be fixable with better tags, or might be structural.

---

## Financials (banks, brokers, card issuers)

Validated on JPM, BAC, WFC, GS, AXP.

### Excluded

| Metric | Reason | Why |
|---|---|---|
| `enterprise_value`, `enterprise_multiple`, `ev_ebitda` | INVALID | EV adds debt and subtracts cash on the theory that debt is financing. For a bank, deposits and borrowings are **raw material** — the input to the business. EV computes a number with no economic meaning. |
| `gross_margin`, `gpa`, `gross_profit_growth` | UNAVAILABLE | No cost of goods. Measured 0.0/16 across all five banks. |
| `current_ratio`, `quick_ratio` | UNAVAILABLE | Unclassified balance sheet — no current/non-current split, because the distinction is meaningless when inventory is money. Measured 0.0/16. |
| **entire Altman Z-score** | UNAVAILABLE | `working_capital / total_assets` is the first component. Working capital is 0.0/16. The score cannot be computed — not approximately, not partially. |
| `debt_equity`, `net_debt_ebitda` | INVALID | Banks run ~10:1 leverage **by design**. High leverage is the business model, not a distress signal. A bank flagged for leverage is just a bank. |
| `interest_coverage` | INVALID | Interest expense is a cost of revenue for a lender, not a fixed charge to be covered. |
| `fcf_margin`, `p_fcf`, `fcf_growth` | INVALID | Free cash flow assumes capex sustains a productive asset base. Banks have no such base. `capex` measured 6.2/16, and the tags that do exist are securities purchases — a completely different quantity. |
| `cash_conversion` | INVALID | Presumes an operating cycle from inventory to cash. Banks have none. |

That's **13 of 41 metrics gone**, including the entire screening step.

### Substitutes — all verified available

Coverage measured across all five banks, 2010+:

| Metric | Formula | Coverage |
|---|---|---|
| `pb` | price × shares ÷ equity | equity **16/16** |
| `roe` | net_income ÷ equity | **16/16** |
| `roa` | net_income ÷ total_assets | **16/16** |
| `net_interest_margin` | `InterestIncomeExpenseNet` ÷ total_assets | **15-16/16** |
| `provision_rate` | `ProvisionForLoanLeaseAndOtherLosses` ÷ total_assets | 10-16/16 |
| `deposits_to_assets` | `Deposits` ÷ total_assets | **16/16** |

**Price-to-book is the primary bank valuation metric** and it works cleanly. This is the one case where the research notes' dismissal of P/B is wrong — P/B is weak for asset-light software companies, but for a bank, book value *is* the business.

Net interest margin and provision rate are the closest available stand-ins for the screening role Altman Z plays elsewhere: NIM measures earning power, provisions measure credit deterioration.

**What's still missing:** Tier 1 capital ratio, the actual regulatory health metric, has no reliable standard `us-gaap` tag. It lives in narrative disclosure. Worth flagging as a known gap rather than faking it.

---

## REITs

Validated on AMT, PLD, SPG, O, EQIX.

### Excluded

| Metric | Reason | Why |
|---|---|---|
| `pe`, `earnings_yield`, `eps_growth` | INVALID | GAAP earnings are systematically understated. REITs depreciate buildings that are typically appreciating, so net income is a depreciation artifact, not economics. The industry uses FFO for exactly this reason. |
| `net_margin` | INVALID | Same depreciation distortion. |
| `gross_margin`, `gpa` | UNAVAILABLE | `cogs` 5.2/16. |
| `current_ratio`, `quick_ratio` | UNAVAILABLE | Unclassified balance sheet, applied inconsistently. 6.4/16. |
| `altman_z_score` | DEGRADED | Working capital 6.4/16 — available for some REITs, not others. Compute where possible, exclude the company from that screen where not. Do **not** substitute zero. |

### Substitutes

| Metric | Formula | Status |
|---|---|---|
| `p_ffo` | price ÷ FFO, where FFO = net_income + depreciation − gains on property sales | ⚠️ **blocked, see below** |
| `dividend_yield` | dividends_paid ÷ market cap | ✅ 13.8/16 |
| `debt_equity` | ✅ meaningful — REITs are levered but not by regulatory design | ✅ |
| `net_debt_ebitda` | ✅ standard REIT leverage metric | ✅ 14.2/16 |

### FFO is not currently derivable — an honest finding

FFO is the correct REIT metric, but the gains-on-sale component has no consistent tag. Measured across the five REITs:

```
AMT   net_income 11/16   dep_amort  0/16   gains 16/16  GainLossOnSaleOfOtherAssets
PLD   net_income 16/16   dep_amort  6/16   gains  6/16  GainLossOnSaleOfProperties
SPG   net_income  0/16   dep_amort 16/16   gains  0/16  (tag present, no annual data)
O     net_income 16/16   dep_amort 16/16   gains 12/16  GainLossOnSaleOfProperties
EQIX  net_income 16/16   dep_amort 16/16   gains  4/16  GainLossOnSaleOfPropertyPlantEquipment
```

Five REITs, five different gain tags, coverage 0-16, and two have gaps in the base inputs too. AMT reports no `dep_amort` under the standard tags; SPG reports no `NetIncomeLoss`.

**Recommendation:** don't ship a half-working FFO. Either invest in REIT-specific tag discovery first (the `03_discover.py` workflow, pointed at these five), or exclude REITs from valuation ranking entirely and score them on leverage and yield until the data supports more. Excluding a sector honestly beats ranking it on a number that's right for two companies out of five.

---

## Utilities and Telecom

Validated on NEE, VZ — a thin sample, treat as provisional.

| Metric | Status |
|---|---|
| `gross_margin`, `gpa` | UNAVAILABLE — `cogs` 4.0/16 |
| `capex`, `fcf`, `p_fcf`, `fcf_margin` | DEGRADED — capex 4.5/16, and utilities are capex-heavy so FCF is structurally negative during build cycles. Negative FCF here signals investment, not distress. |
| `debt_equity` | VALID but recalibrate — regulated utilities carry high leverage by regulatory design. Rank within sector; don't apply cross-market thresholds. |
| `dividend_yield` | VALID and central — the primary reason to hold the sector. |

---

## Energy

Validated on XOM (after CIK correction), CVX, COP. Coverage is good across the board.

The issue here isn't availability, it's **cyclicality**:

- `pe`, `earnings_yield` — swing violently with commodity prices. A trough-earnings P/E looks catastrophic and a peak-earnings P/E looks cheap, both misleadingly.
- `ev_ebitda` — more stable, preferred. This aligns with the research notes' general preference for enterprise multiples.
- Consider normalizing earnings over a full cycle (5-7yr average) rather than trailing twelve months.

---

## Technology, Consumer, Healthcare, Industrials

All 41 metrics apply. These are the sectors the standard toolkit was designed for. Coverage is 14-16/16 nearly everywhere after the tag-map fixes.

One note: `gross_margin` and `gpa` are strongest here (Tech 14.4, Healthcare 16.3) — which matters, because Gross Profitability is the quality metric the research singles out as least manipulable. It works best exactly where it's most available.

---

## Renormalization

When metrics drop out, the composite must renormalize or sectors become incomparable.

```
1. Look up the company's sector via Company (joined on ticker)
2. For each metric group, filter to metrics applicable to that sector
3. If fewer than MIN_METRICS remain in a group, exclude the group entirely
   and renormalize across the remaining groups
4. Renormalize weights within each surviving group to sum to 1.0
5. Combine groups by their group weights, themselves renormalized
```

Same `weights / weights.sum()` pattern already used in `get_weighting()` — applied at two levels.

### Worked example — a bank

```
Valuation group:  9 metrics defined
                  ev_ebitda, enterprise_multiple, enterprise_value  EXCLUDED (invalid)
                  p_fcf                                             EXCLUDED (invalid)
                  → 5 remain: pe, pb, ps, price_operating_cash_flow, earnings_yield
                  → renormalize those 5 to sum to 1.0

Health group:     Altman Z, current_ratio, quick_ratio, debt_equity,
                  net_debt_ebitda, interest_coverage  ALL EXCLUDED
                  → 0 remain → group dropped entirely
                  → substitute the bank health group: NIM, provision_rate,
                    deposits_to_assets, equity/assets
```

### The trap to guard against

If a group shrinks from 9 metrics to 2, those 2 carry 4.5× their normal influence. A single bad data point can then swing the whole score.

**Set `MIN_METRICS` per group (3 is a reasonable start).** Below it, drop the group rather than let it be dominated by survivors. And **log every exclusion** — a company silently scored on 12 of 41 metrics looks identical in the output to one scored on all 41. That's the "no silent caps" rule applied to scoring.

---

## Proposed `criteria.yaml` structure

```yaml
sector_applicability:

  defaults:
    min_metrics_per_group: 3

  # Metrics EXCLUDED per sector. Anything unlisted applies.
  exclusions:
    Financials:
      valuation: [enterprise_value, enterprise_multiple, ev_ebitda, p_fcf]
      quality:   [gpa, gross_margin, fcf_margin, cash_conversion]
      health:    [altman_z_score, current_ratio, quick_ratio,
                  debt_equity, net_debt_ebitda, interest_coverage]
      growth:    [gross_profit_growth, fcf_growth]

    REIT:
      valuation: [pe, earnings_yield]
      quality:   [gpa, gross_margin, net_margin]
      health:    [current_ratio, quick_ratio]
      growth:    [eps_growth, gross_profit_growth]

    Utilities:
      quality:   [gpa, gross_margin]
      valuation: [p_fcf]

  # Sector-specific groups replacing an excluded one.
  substitutions:
    Financials:
      health:
        - net_interest_margin
        - provision_rate
        - deposits_to_assets
        - equity_to_assets

  # Sectors where a metric is valid but thresholds differ. Rank within
  # sector; never apply cross-market absolute cutoffs.
  rank_within_sector_only:
    - debt_equity
    - net_debt_ebitda
```

---

## Open decisions

**1. What happens to a bank at the screening step?**

Altman Z is your only absolute cutoff, and banks can't have one. Three options:

- Pass banks through screening unfiltered (they're only ranked, never eliminated)
- Build a bank-specific screen from equity/assets and provision trends
- Exclude Financials from the universe entirely for v1

For a testing-phase universe of large-cap names, **passing them through unfiltered is defensible** and by far the simplest — but write it down as a deliberate choice, because "banks are never screened out" is a real bias that should be visible, not accidental.

**2. Should a sector-excluded metric count as missing or as absent?**

The research notes recommend assigning the median (50) to missing data so one gap doesn't eliminate a company. But that's for *unknown* values. A sector-excluded metric isn't unknown — it's inapplicable. Assigning 50 would let a bank score middling on enterprise multiples it doesn't have.

**Exclude and renormalize. Never impute.** The two cases need different handling, and only the first deserves a median.

**3. Sector granularity.**

`Company.sector` is a single GICS-style string. But "Financials" spans deposit-taking banks, brokers, and card issuers — GS and AXP differ meaningfully from JPM. The exclusion lists above are conservative enough to hold across all three, but if bank scoring becomes central, `industry` (already on `Company`) is the finer knob.

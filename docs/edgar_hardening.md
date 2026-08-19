# Tag Map Hardening — S&P 500 Pass

The [original coverage study](edgar_coverage.md) validated the tag map on 32 companies. This pass ran it against a **180-company stratified sample of the S&P 500** (20 per sector across 9 sectors) to find what the smaller sample missed.

Scripts: `scripts/05_universe.py` → `08_harden.py`. Deliverables: an expanded `configs/xbrl_tags.yaml` and `data/companies_seed.csv`.

---

## The headline: most "gaps" are not gaps

The gap report flagged 19 fields with missing coverage somewhere. Investigating each, **the large majority are correct absences, not tag-map failures**:

| Apparent gap | Reality |
|---|---|
| `preferred_equity` — 95 companies | Almost all simply have no preferred stock. Absence = 0.0. |
| `dividends_paid` — 30 companies (ADBE, AMD, ALGN, ABNB…) | These pay no dividend. Confirmed: zero dividend tags of any kind. Absence = 0.0. |
| `interest_expense` — low-debt tech (ANET, ALGN) | `LongTermDebt` = 0. No debt means no interest. Absence ≈ 0.0. |
| `cogs` — utilities, energy | Structural, as documented — no cost-of-goods line. |
| `current_assets/liabilities` — 14 REITs | Unclassified balance sheets. Structural. |

**This is the single most useful finding for the ingestion code:** a missing field usually means the company genuinely has zero, not that a tag is missing. The pipeline should distinguish *"no tag because no such item"* (→ 0.0) from *"no tag but the item exists"* (→ investigate). The fields above fall in the first bucket.

The danger is treating these as errors and hunting for tags that don't exist — hours of work chasing numbers that were correctly absent.

---

## Genuine tag additions (applied to `xbrl_tags.yaml`)

Four real variants surfaced that the 32-company sample never hit:

| Field | Added tag | Evidence |
|---|---|---|
| `interest_expense` | `InterestAndDebtExpense` | 14/180, concentrated in materials/chemicals (ALB, APP) — a real income-statement line those filers use instead of `InterestExpense` |
| `interest_expense` | `InterestPaidNet` | 136/180 — **fallback of last resort only** (see caveat) |
| `total_debt` | `UnsecuredDebt`, `SeniorNotes` | insurers (AIZ: 16yr) report debt by instrument, not as one line |
| `preferred_equity` | `PreferredStockValueOutstanding`, `PreferredStockIncludingAdditionalPaidInCapital` | minor variants, a few companies each |

### The `InterestPaidNet` caveat — a semantics trap

It covers 136/180, which is tempting. But it's the wrong statement: `InterestPaidNet` is interest **paid** (cash flow), while `interest_expense` is interest **expensed** (income statement). They differ by accruals — the cash you sent out this year vs the cost you recognized this year.

For the Altman `interest_coverage` and any margin work, you want the income-statement figure. So `InterestPaidNet` sits **last** in the candidate list: used only when every real interest-expense tag is absent, and flagged in the config so future-you knows the number shifted meaning.

This is the kind of thing that looks like a coverage win and is actually a correctness bug. Worth the note.

---

## CIK reorg detection worked

The reorg detector (`concept count < 150` → suspect) ran across all 180 and flagged exactly one: **XOM, 94 concepts**. That's the Exxon holding-company reorganization from the first study, caught automatically this time rather than by hand. Override already in `cik_overrides`.

No other S&P 500 name in the sample tripped it — reassuring that Exxon is an edge case, not a widespread pattern. But the detector is now a standing check, so the next reorg gets caught on ingest instead of silently producing an empty company.

---

## Deliverable: `data/companies_seed.csv`

All 503 S&P 500 companies, ready to load into the `companies` table.

| Column | Source | Trust level |
|---|---|---|
| `ticker`, `name`, `sector`, `industry`, `cik` | S&P constituents + SEC | **factual** |
| `company_type` | 3yr revenue CAGR heuristic | **starting point, review before trusting** |
| `type_signal` | the CAGR that drove the guess | diagnostic |

`sector` is mapped from GICS into your internal buckets (Information Technology + Communication Services → Technology; Real Estate → REIT; Consumer Discretionary + Staples → Consumer).

### `company_type` is a starting guess, not an answer

480 Mature, 23 High-Growth, 0 Early-Stage (correct — the S&P 500 has no early-stage companies by definition). But two caveats you must respect before using it:

1. **Only 180 of 503 got a real signal.** The other 323 defaulted to Mature without data. Those defaults are plausible (S&P 500 skews mature) but unverified.

2. **Revenue CAGR is a crude proxy and it misfires.** Among the 23 High-Growth flags:
   - **CCL (Carnival), 30%** — that's COVID recovery off a near-zero 2021 base, not growth
   - **CBOE, 53% / APO, 43%** — M&A and accounting changes, not organic growth
   - **ANET 27%, AXON 33%, AVGO 24%, APP 25%** — these are genuinely high-growth

`company_type` is the input that selects your entire pillar-weight vector, so it deserves a human judgment, not a CAGR. Treat the 23 as *candidates to review*, confirm the real ones, and the rest stay Mature. The `type_signal` column is there so you can see what the guess was based on and overrule it.

---

## What this changes for ingestion

1. **Missing ≠ error.** Code a three-way distinction: value present, structurally absent (→ 0.0), or genuinely unknown. The 95 preferred-equity and 30 dividend absences are the common case, and they're zeros.

2. **Run the reorg check on every fetch.** Concept count < 150 for an S&P-scale company means find the predecessor CIK before storing.

3. **`InterestPaidNet` is a labeled fallback**, not a peer of the real tags.

4. **`company_type` needs a human pass** before the seed drives any scoring.

---

## Addendum — full 503-company pass

All 503 S&P 500 constituents are now cached (`scripts/09_fetch_remaining.py`, `10_retry_failed.py`). `data/companies_seed.csv` was regenerated with the 3yr revenue-CAGR signal computed from **real data for every company**, not the 180-company sample plus 323 blind defaults from the first pass — 65 flagged High-Growth (up from 23), still candidates for your review, not final classifications.

`data/data_quality_matrix.csv` (`scripts/11_matrix.py`) — every company × 27 fields, each cell `OK` / `THIN` (<5yr) / `MISSING` / `N/A` (sector-structural). **498/503 companies clear a basic screenability bar** (revenue, net_income, total_assets, equity, cash all present). Mean field coverage 93.3%, ranging Materials 97.0% down to Utilities 88.5%.

### The 5 non-screenable companies, individually resolved — not summarized away

| Ticker | Cause | Fix |
|---|---|---|
| **XOM** | Matrix ran against the un-overridden thin CIK (94 concepts) — the `cik_overrides` entry exists in the config but the matrix script fetches raw, it doesn't apply overrides. **This is a real finding**, not a data problem: it confirms overrides must be applied at fetch time in `fundamentals.py`, not treated as documentation only. | Apply `cik_overrides` before caching, not after. |
| **HONA** | Honeywell's Aerospace division spun off as an independent filer in Oct 2025 (confirmed via the `/submissions/` endpoint — first filing date 2025-10-01). Genuinely new company; thin history is correct, not a bug. HON (the original, CIK 773840) kept its full history and correctly wasn't flagged. | No override — a new company has no predecessor to point to. Needs a data-sufficiency screen (min years of history) at the scoring layer, separate from the reorg-override mechanism. |
| **FDXF** | Same pattern — FedEx Freight spun off as an independent filer in 2025. | Same as HONA. |
| **APA** | 360 total concepts (not thin) but no top-line revenue tag found among standard candidates or E&P-specific ones searched. History only goes back to 2019, which is suspicious for a company this old — APA Corporation was created in 2021 when Apache Corp reorganized into a holding structure. **Likely a second Exxon-style case** — the pre-2021 Apache Corp history may be orphaned under a different CIK. Not confirmed; flagged as a lead for the next person who touches this, using the same `/submissions/` check that found XOM and HONA. | Investigate via `/submissions/CIK{apa_cik}.json`, same method as XOM. |
| **SYF** | Synchrony Financial (spun off from GE in 2014, ~11yr real history — not thin). Reports revenue as two separate components: `InterestIncomeOperating` (14yr) + `NoninterestIncomeOtherOperatingIncome` (14yr), consumer-finance/card-issuer style. This is a genuinely different problem from the bank `RevenuesNetOfInterestExpense` pattern already in the tag map — it needs a **sum**, not a fallback candidate. | Scoped but not implemented: add a `revenue = InterestIncomeOperating + NoninterestIncomeOtherOperatingIncome` derivation for consumer-finance names, analogous to how `dep_amort` sums two components. Left undone deliberately rather than guessing at the formula without checking more card-issuer filings first. |

Net: **3 of 5 are confirmed correct behavior** (HONA, FDXF, and XOM once the override is wired into the fetch path), **1 is a scoped follow-up** (SYF), and **1 is a genuine open lead** (APA) worth ten minutes with the `/submissions/` endpoint next time someone's in this code.

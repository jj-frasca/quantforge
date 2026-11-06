# ADR-418: Seal a prospective published quality/value portfolio

- **Status:** Accepted — prospective protocol only; no outcome yet
- **Date:** 2026-11-06
- **Deciders:** Codex W45 session 3 under standing autonomy
- **Relates to:** ADR-024/029/095/142/143/417; FINDING-351

## Decision, hypothesis and independent review

Seal one actually prospective long-only combined-score top-quintile portfolio.
Hypothesis: its funded net return strictly exceeds the equally funded eligible
universe, SPY and cash over the fixed future interval below. A positive result
is only an economic lead. No alpha, statistical significance or graduation is
claimed from this single short common-calendar observation.

Independent research-expert approved the design before selection, including a
fixed attempt root, expiry rules, prohibition on interim study economics and
explicit unresolved source risk. The mission was reread after ADR-417's exact
CI passed. This is a new future cohort with a new dated published input, not a
retry, repair, continuation, pooling or replacement of ADR-417. ADR-417 stays
permanently UNEVALUABLE, with no further acquisition or subset calculation.

## Inputs and selection fixed before ranks

Pin full published revision `7048c785fd34fa0fc5b8357fc711929c7fe48fb9`:

- Fundamentals SHA256: `b59375cd295f2d7582bed762b856f1f496cdc246d94b916e32025cb2069d4ff6`
- S&P roster SHA256: `ee973b82b0fba4471d6c248330929dfc0c8e4589aeb3e0cea678c1e042b38040`
- Paths: `data/fundamentals_pool.json`, `data/universes/sp500.txt`.
- Publication evidence: successful push-triggered CI42225157084 and hooks42225157001,
  both full SHA above, created 2026-11-06T13:23:49Z; CI completed13:27:26Z.

Publication proves these opaque scores were available before entry; filing
periods, per-fact PIT authenticity and score correctness remain qualified by
FINDING-322/324/335. Never recompute or update scores, substitute a later pool,
filter on diagnostic flags, add symbols or resolve ambiguity using later data.
Include every roster member with a non-null combined score; refuse duplicate
symbol/CIK identities. Rank descending combined, ties ascending CIK then symbol;
take ceil(n/5). Initial equal-dollar allocations; fixed normalized units thereafter.
Seal every eligible original score/flag/citation plus eligible/selected order,
input hashes, dates, account, cost, source and trial rules in one exclusive artifact.

## Untouched geometry and deadlines

Entry: **2026-11-09 close**. Exit: **2027-02-10 close**. There are **64 scheduled
session closes /63 return intervals**: weekdays inclusive, excluding2026-11-26,
2026-12-25,2027-01-01,2027-01-18. Nov27 and Dec24 are13:00 America/New_York
closes; other sessions16:00. Entry/exit are21:00UTC. This uses the exchange's
[2026/2027 calendar](https://ir.theice.com/press/news-details/2025/NYSE-Group-Announces-2026-2027-and-2028-Holiday-and-Early-Closings-Calendar/),
announced2025-12-23 and verified2026-11-06 before adoption.

The protocol+cohort must be published with exact green CI **before2026-11-09
14:30UTC** (entry-day open), otherwise status is permanently **EXPIRED**. Do not
slide entry/exit dates or reseal on a later snapshot. No training window, selection
on future returns, interim study price acquisitions, economic computations,
weekly scorecards or sequential looks. Unrelated daily hunts/paper workflows may
observe these symbols; disclose accidental outcome exposure without changing the
frozen policy or adding a look. No study market prices were acquired at sealing.

One final evaluation is permitted in **[2027-02-11T00:00Z,2027-02-12T00:00Z)**.
A missed window is permanently EXPIRED, never a renewed budget. If an unforeseen
market closure changes the fixed calendar, record UNEVALUABLE rather than altering
it after exposure. No extension, additional session or changed threshold.

## Funded account and costs

One capital unit, no leverage/shorts/interest/rebalancing. At per-side c=0.001,
units_i=1/[k*(1+c)*entry_adjusted_price_i]. Mark the same units each date and sell
at exit, net cash=(1-c)*terminal_notional. Gross companion has zero assumed cost;
net economics always charge both sides. Eligible-universe EW and SPY controls use
the identical funded entry/exit account; cash remains1. Compute gross/net returns,
net excess vs all3 controls, fees, actual dollar turnover vs initial capital,
maximum drawdown including initial cash/all pre-sale marks/final cash, and exposure
100% securities after entry/0 after liquidation. Use the reviewed ADR-417 funded_hold
recipe at revision7048c785, never its frozen historical acquisition driver/calendar.
Adjusted closes are canonical six-decimal dividend/split-adjusted total-return
proxies with normalized units, not broker shares, cash-dividend ledgers or fills.

## Future source attempt and preservation

Fixed attempt root: `/tmp/qf-adr418-prospective-20261109-20270210`.
Do not create it before the final window. Exclusive start marker binds this
manifest and exact executed code/dependency identities before any acquisition.
Any interrupted start stays permanently INCOMPLETE; no resume/retry/reroot.
A future driver needs TDD and independent research/data review for conformance
before execution; this protocol is not permission to alter another frozen runner.

Only free no-key yfinance, one default adapter attempt per required name in sealed
eligible order then SPY, using the pinned revision's canonical normalization and
DataQualityEngine policy. Request bounds2026-11-09T00:00Z through2027-02-11T00:00Z.
Vendor auth internals are not certified as one HTTP call. Every name+SPY must cover
all64 session labels exactly; no common-calendar intersection/drop/fill, proxy,
replacement, later name/CIK mapping or alternate vendor. Preserve raw canonical
bars, SHA256, original full quality report even on failure, passing dataset evidence,
actual dependency/code hashes and all warnings. First fetch/quality/calendar failure
ends the whole cohort **UNEVALUABLE**, no subset performance or screen verdict.

ADR-417 failed on AVB at request23/284: sealing does not solve this demonstrated
all-or-nothing vendor-coverage risk. UNEVALUABLE is not negative economics. Do not
request old ADR-417 missing bars or reuse its partially fetched sources here.
No cloud dispatch, paid resource, scheduler, paper-broker or real-money action.

## Trial accounting, error criteria and acceptance

One new prospective policy, three controls, no searched variants. Related prior
technical hunts, quality/value searches, ADR414–416 including extra and failed-push
attempts, and ADR417's unevaluable attempt remain disclosed prior selection. Do not
reset effective N to1 or pool old and new cohorts. Freeze the represented current
cross-sectional pool count/max/hash as context, not a reconstructed effective N.

One final economic screen, strict positive net excess over **all3** controls;
otherwise screenFAIL. Missing evidence=>UNEVALUABLE, missed deadlines=>EXPIRED,
interrupted acquisition=>INCOMPLETE. No cost-tier, horizon, quantile, universe or
threshold retries. No cross-company bootstrap or p-value: observations share one
calendar and one prospective episode. No annualized alpha inference.

PBO, DSR, parameter stability, WF, locked holdout and graduation remain **NOT
MEASURED** at this64-close/single-config geometry. The existing252-search+
252-holdout floors stay; no dummy grid, threshold waiver or promotion. Future
full-gate claims still need sufficient truthful score vintages and proper related
selection accounting. Even an economic screenPASS supplies only a lead requiring
separately reviewed untouched evidence before an alpha claim.

## Reversal

Before entry, explicitly cancel and record CANCELLED without replacing this cohort.
After entry, retain all frozen inputs and interpret under this protocol. Removing
an evaluator never authorizes erasing this registration or obtaining another look.

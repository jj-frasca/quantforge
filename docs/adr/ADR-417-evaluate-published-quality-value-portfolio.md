# ADR-417: Evaluate a published quality/value portfolio after publication

- **Status:** Accepted; retrospective exploratory protocol, fixed before ranks or new prices
- **Date:** 2026-11-06
- **Deciders:** Codex W45 session 3 under standing autonomy
- **Relates to:** ADR-024/029/095/142/143/161/242/413–416; FINDING-351

## Context and independent review

The quality/value mission requests a long-only top-quintile combined-score portfolio.
Existing `xs_quality`/`xs_quality_value` experiments exist: they broadcast static scores
across historical prices and use dollar-neutral long/short legs. ADR-416's completed
history-length study remains closed. Neither establishes a funded long-only policy's
post-publication economics. Repeating either is not this task.

Independent research-expert pre-adoption review approves this bounded exploratory
comparison, explicitly refusing confirmatory OOS or gate-success claims. The historical
publication timestamp establishes availability of opaque scores, not per-fact filing
correctness. FINDING-322/324/335 qualifications still apply.

## Hypothesis and fixed comparison

Published combined-score leaders outperform the same eligible universe and SPY after
identical costs. Use only commit `ca73b3047fe4a6bc6e312ce7fa94bb351215af1a`:

- `data/fundamentals_pool.json`, SHA256
  `175333955ac62b5cc4aa42822968f2aba944234dbf391af595b9197e0c644af6`;
- `data/universes/sp500.txt`, SHA256
  `ee973b82b0fba4471d6c248330929dfc0c8e4589aeb3e0cea678c1e042b38040`.

Successful workflow32145869280 recorded publication 2026-08-18T14:13:24.4427047Z
(prior session log `/tmp/qf-w45-s1-fundamentals-publication.log`). Git commit
creation alone is not publication proof. Validate that receipt before acquisition.
Keep every roster name with a non-null combined score, with no flag-based exclusion.
Refuse duplicate/ambiguous eligible symbol or CIK identities. Rank descending combined,
then ascending CIK and symbol; take ceil(n/5). No score recomputation, later pool, name
replacement, alternate universe, cost tier, quantile, holding horizon or factor variant.

## Evaluation geometry, account and costs

One initial capital unit; enter at adjusted close **2026-08-19**, exit at adjusted
close **2026-11-05**. Fixed daily session labels: weekdays in that inclusive window
except NYSE Labor Day 2026-09-07. All required names and SPY must cover that exact
calendar. No intersection/drop/fill. No return before entry earns money. There is
no fitting window; these historical outcomes are exploratory, not an untouched
holdout. The future after this protocol remains unused; no prospective experiment
is authorized by this document.

Selected and eligible-universe controls each use initial equal dollar allocations,
fixed normalized units thereafter, no rebalancing, no leverage, no shorting, no cash
interest. SPY uses the identical account; cash remains one. At c=0.001 per side,
units_i=1/[k*(1+c)*p_i(entry)]. This funds entry commissions from capital. Mark equity
as sum(units_i*p_i(t)); liquidate terminal holdings times (1-c). Gross companion uses
c=0. Report gross/net returns, matched net excess, entry+exit dollar turnover relative
to initial capital, fees, maximum drawdown including initial capital, every pre-sale mark and terminal
liquidation, and exposure (100% securities after entry, 0 after exit). Adjusted prices
represent a dividend/split-adjusted total-return proxy with normalized units, not
literal broker shares or a cash-dividend ledger. Costs are assumed, not measured fills.

## Source, one attempt and preservation

Only free no-key yfinance via existing canonical normalizer and DataQualityEngine.
Default adapter single-attempt policy; vendor-internal authentication behavior is
not certified as one HTTP request. Request Aug19 UTC through Nov6 UTC, validate daily
labels without changing normalized price values. Retain each successful canonical
bar payload, full quality evidence, adapter/code identity and SHA256. Warnings stay.
No vendor-truth claim. First fetch/quality/calendar failure ends the study UNEVALUABLE;
no partial return, replacement, retry, resume, re-root, different window or source.

Root `/tmp/qf-w45-s3-adr417` is exclusively created before acquisition; a durable
start marker and frozen selection precede every fetch. Interrupted starts remain
incomplete permanently. Replay of retained bytes for verification is allowed, new
acquisition is not. No repository generated JSON, cloud dispatch or broker action.

## Selection/trial accounting and acceptance

One new economically specified policy evaluation, not a new 200-config search.
Three controls (eligible equalweight, SPY, cash), not extra policy selections.
Historical technical searches, quality/value snapshots, ADR414/415 compound runs and
ADR416 including its failed-to-publish and extra attempts are prior related selection;
none is reset, pooled as independent evidence or omitted to make N=1 credible. Save
current cross-sectional experiment count and represented lifetime maximum before
acquisition, plus raw pool hash. Do not write synthetic trial counts into cloud pools.
Any future formal DSR analysis must carry prior selection and unpersisted-attempt
uncertainty; this study's single policy does not certify an effective trial count.

Economic screen succeeds only if net return exceeds **all three** controls (strictly
positive excess vs eligible EW, SPY and cash). Otherwise it fails; missing evidence
is UNEVALUABLE. No threshold is tuned. Even a screen success is only a lead: one
shared short calendar provides no independent-company inference, no p-value/CI is
claimed, and no reliable annualized alpha is inferred. PBO, DSR, stability, WF and
locked-holdout gate status are **NOT MEASURED**, never passed: one fixed config and
<504 bars cannot supply the existing 252-search +252-holdout geometry. Do not fabricate
a grid or relax floors. A later independently reviewed prospective protocol with
sufficient truthful history is required before any alpha/gate claim or promotion.

## Alternatives and reversal

Current-score historical backfill was rejected for look-ahead. A fresh full hunt was
rejected because it repeats a static-score conditional measurement rather than the
requested account. Doing nothing wastes a real published input archive. Remove the
standalone evaluator to reverse capability; keep this protocol and result as history.

# ADR-301: Validate original holdout evidence at gate consumption

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 23, ISO 2026-W42
- **Resolves:** FINDING-255
- **Extends:** ADR-015/016/102/160/162/296

## Context

GraduationGate consumes a frozen but unvalidated HoldoutScore dataclass. Synthetic
public calls pass the gate with benchmark Sharpe=-infinity, boolean Sharpe/history,
float history, NaN total return or return=-2. GateResult does not retain benchmark
or total return, and coercion erases original Sharpe/count types. Graduate later
rejects invalid returns, but does not recover original types or benchmark evidence.
These are standalone boundary defects, not actual production corruption, market
false graduates or changed calibration rates. Ordinary score_on_holdout computes
finite statistics through the backtest engine; no provider or search is involved
in these counterexamples.

## Options considered

1. Validate the complete original bundle at consumption: one clear gate boundary,
   preserves construction and other consumers; explicitly tightens malformed calls.
2. Validate only benchmark Sharpe: smallest patch but leaves the other demonstrated
   original-evidence holes at the same consumer.
3. Replace HoldoutScore with a validating model or change its constructor: affects
   other consumers and serialization beyond this evaluator's demonstrated need.
4. Add benchmark/return fields to persisted verdicts: may improve future provenance,
   but changes schemas without itself preventing malformed input comparisons.

## Decision

After existing report revalidation, MinBTL/count checks and available-duration
validation, validate the whole supplied holdout bundle before any gate predicate.
Require original positive nonboolean Integral n_bars using require_trial_count;
normalize only the local published count to Python int, leaving the source intact.
Then require original nonboolean Real sharpe, total_return and buy_and_hold_sharpe,
with finite float inspection and explicit ValueError on failed inspection. Inspect
without replacing source operands. Require original total_return > -1, preserving
wealth; exact Fraction(-1)+epsilon remains valid even when float rounds to -1.

Validate all fields even when another gate component will fail or
require_beat_buy_and_hold=False. An inactive comparison stays inactive: valid
benchmark scores of any finite sign remain supported and no benchmark threshold
is added. This is complete-bundle validity independently of configuration, rather
than conditional acceptance of malformed evidence.

Preserve all native score comparisons, reasons, configuration fields/hash,
HoldoutScore construction/serialization, score_on_holdout math, GateResult and
Graduate fields, search/accounting-v14 fingerprints and generated/frozen records.
No estimator, selector or threshold changes; no calibration rate is remeasured or
inferred. This checks scalar
domains, not whether history matches a held-out frame or benchmark provenance
matches symbol/period. FINDING-256 separately records the preexisting exact-real
projection limitation: finite float inspection does not guarantee that published
float evidence can replay original strict comparisons. Do not claim it does.

## Consequences, verification and reversal

Malformed original evidence refuses before a verdict even when a field is unused
by an active predicate. All valid ordinary Python-float behavior stays exact.
Observe actual RED before implementation. Cover all fields, error precedence,
inactive benchmark policy, original Fraction boundaries, integral normalization,
nonpositive Sharpe, wealth boundary and finite native scalar representations.
Hypothesis checks native gate predicates for valid holdouts. Compare 288 frozen
valid baseline outcomes byte-for-value and independently review scope. Run full
foreground make check-all before individual delivery and exact master CI.

Remove only the consumption guard and local count normalization to reverse,
reopening FINDING-255. This does not authorize cohort reruns or record migration.

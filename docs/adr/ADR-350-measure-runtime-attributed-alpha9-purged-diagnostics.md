# ADR-350: Measure runtime-attributed Alpha9 purged diagnostics

- **Status:** Accepted
- **Date:** 2026-10-23
- **Deciders:** Codex autonomous session22, ISO2026-W43
- **Extends:** ADR-325/348/349
- **Addresses in part:** FINDING-265; preserves FINDING-272

## Context

ADR-349's stable factory and distinct Alpha9-v3 readers are individually published
and exact master CI green. Alpha9 still reports unsupported_factory. Independent
operator/kernel and deterministic endpoint review supports a restricted recipe.
The signal differences prices before trailing min/max sign tests: d[t]=p[t]-p[t-1].
W differences reach price t-W; previous weights and current turnover extend the
net-return hull to [t-W-1,t]. D=W+1, shipped lags4/6/11, differs from high's D=W.
Only row0 is flat; incomplete extrema cause early -d signals from row1. Preserve
these semantics without changing signal or portfolio arithmetic.

The exact tagged primary source is
[pandas3.0.6 extrema](https://github.com/pandas-dev/pandas/blob/v3.0.6/pandas/_libs/window/aggregations.pyx#L913-L1051).
Both roll_min and roll_max use the same deque helper with opposite comparisons.
Monotone fixed bounds expire stale candidates; newer dominating operands expire
no earlier than discarded ones. Returned extrema select local input operands.
The fixed initial NaN difference has price-independent validity; finite positive
Float64 prices yield finite differences thereafter. Installed default dispatch,
fixed-window indexer and option selector match the ADR-348 reviewed sources.
This certifies neither arbitrary builds/patches/concurrent mutation nor Numba,
future versions, other reducers, independence or historical PIT availability.

Independent bounded controls show oldest-price perturbations change previous
weights, gross and turnover for all3 windows; earlier-prefix perturbations leave
all operands at t exact. Current-price changes leave earlier outputs exact.
Sliding extrema/conditional and prefix oracles agree, including early trades.
E=D-1 shares a source price at both train/test boundaries; E=D separates them.
These controls supplement the operator proof, not a calibration or rate claim.

## Decision

Support only exact xs_alpha9/alpha9_factory identity, native Float64 complete
positive panels and actually allocated nonboolean Integral windows3/5/10.
Use max(actual W+1) and E=max(original floor,D), never shrink E to fit.
Reuse unchanged matrix/evaluator and each family's actual kept-fold benchmark.
Measured/no-fold Alpha9 uses ADR-349 v3/rolling-alpha9-v1; high remains v2/D=W
and the three shifted families remain v1. Other domains retain explicit
unsupported outcomes and primary eligibility; numerical evaluator errors propagate.

Reuse frozen HighRuntime and capture_high_runtime, whose historical names remain
for compatibility: their fields describe pandas version/engine observations, not
a high-only scientific recipe. Extend per-config before/after capture at the
existing _config_returns only for exact known high or Alpha9 allocation keys,
names and factories. Keep unrelated-key short-circuit for manual/custom stubs.
Require agreement within each call and across that family's allocated configs;
carry each family's receipt with its matrix. Different families may have distinct
saved domains. Missing known-Alpha9 receipt raises; custom same-name replacements
remain unsupported_factory. Classify saved receipts without rereading globals.
Only pandas3.0.6/use_numba=False supports the reviewed recipe; existing version
and engine refusal reasons remain. Never force an engine or mutate an option.
Caller-supplied receipts are bounded metadata, not a hostile-code provenance proof.

Supersede ADR-349's actual-Alpha9 blanket unsupported assertion with exact-domain
support and unaudited-domain refusal, retaining its other assertions. Update public
recipe qualifications and cold memory without changing prior numeric evidence.
No selector, estimator, primary formula, threshold, fingerprint, longitudinal-v14,
generated record or frozen cohort changes. New measurement errors may refuse a
formerly completed search; unchanged formulas do not certify unchanged rates.
Later training, whole-sample family choice, internal costs without account
switching reconciliation, no extra benchmark turnover costs and absent panel-null
calibration remain explicit. Unsupported-family FINDING-265 remains Open in part.

## Alternatives and reversal

Late global checks misattribute execution. Reusing high's W/v2 misstates both
the dependency chain and scientific recipe. Forcing Cython changes primary
execution. Universal rolling support contradicts FINDING-272. Retaining deferral
leaves an audited measurable gap. Choose restricted captured-runtime support.

Reverse only Alpha9 support and its capture branch. Retain published readers,
written findings and every generated historical record. Further runtime domains
or scientific recipes require their own reviewed decision.

## Verification

Observe RED before implementation. Test saved-safe/unsafe metadata, no late reads,
before/after and cross-config mismatches, independent family receipts, missing
receipt/custom precedence, actual allocated maxima, no-fold/large floors, actual
kept-fold pairing, numerical refusal and mixed store/API/client roundtrips.
Fake unsafe metadata only; do not execute Numba. Hypothesis covers source hull
locality and both embargo endpoints. Preserve full primary/WF/gate/accounting
payloads except intentional PCV evidence and UUID/time; preserve high/shift outputs,
old tests except the explicit supersession, unrelated AST/data bytes and hashes.
Independent research/frontend review and fresh foreground make check-all precede
individual publication and exact master CI. No provider, cohort or calibration
measurement is authorized beyond deterministic synthetic unit fixtures.

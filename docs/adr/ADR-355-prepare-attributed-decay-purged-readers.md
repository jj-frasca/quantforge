# ADR-355: Prepare attributed decay-reversal purged readers

- **Status:** Accepted
- **Date:** 2026-10-23
- **Deciders:** Codex autonomous session24, ISO2026-W43
- **Extends:** ADR-325/347/349/352/354
- **Related:** FINDING-265/272

## Context

ADR-354's stable decay factory is individually published and exact CI green.
The actual producer remains unsupported. Subsequent read-only tagged NumPy
adapter/DOUBLE_dot and conforming DDOT review finds fresh bounded vector operands,
not an expired-window accumulator. BLAS rounding and vendor reproducibility are
separate from operand locality; no arbitrary binary/build attestation is claimed.
Deterministic public-portfolio endpoints support prospective D=W+1 for shipped
windows3/5/10, distinct from Alpha4's W. The signal follows pct_change into a
rolling.apply dot callback with first W NaN rows, not a percentile or extrema.
Existing finite-return validation remains necessary: finite prices alone cannot
guarantee finite ratios. These prospective controls do not adopt a producer or
runtime policy, and FINDING-272's rolling-sum/variance limitation remains.

## Decision

Install exact method
`restricted-pandas-3.0.6-numpy-2.5.4-cython-decay-reversal-purged-equal-weight-continuation-v5`
and rule `rolling-decay-reversal-v1` in existing backend/API/client readers.
Only measured/no_usable_folds can carry v5, requiring its exact rule and maximum
allocated lag4/6/11. V5 cannot carry another rule, and other methods cannot carry
the new rule, including Alpha9-v3 which shares those lag values.

Full source trials bind xs_decay_reversal, exactly window/quantile parameters,
original nonboolean Integral window3/5/10 after inherited Trial normalization,
and maxlag>=window+1. Keep all existing count/finite/scalar/embargo/kept-geometry,
immutable reconstruction, complete common-request and attributed WF-bar checks.
Recognized v1-v5 may coexist; defaults and historical absence stay exact. Compact
wire readers retain their existing structural scope without replaying finalist
parameters, allocated source configs, runtime execution or provenance.

Retain the identity through Zod and render a plain-language pandas3.0.6
Cython/NumPy2.5.4 decay-weighted-return qualification inside existing Fold evidence.
Keep raw method/rule IDs out of product copy. Preserve the actual support caption
exactly: this prepares readers, it does not add a supported producer. Historical
rows receive no invented runtime/fold qualification. Later training, whole-sample
family choice, continued internal costs without switching-account reconciliation,
benchmark costs, mean-of-Sharpes and PIT/calibration limitations remain.

Do not change stable factories, signal/callback/ranker, support_lag, measurement,
matrix generation/captures or evaluator. Actual decay remains unsupported_factory.
A separate scientific ADR/TDD must govern saved generation-time NumPy/pandas/
engine attribution, per-config before/after agreement, actual allocated maximum,
actual kept-fold pairing and completed endpoint/dependency evidence. No score,
threshold, selector, fingerprint, longitudinal-v14, generated or frozen record
changes; no provider/cohort/calibration measurement is authorized here.

## Alternatives and reversal

Reusing Alpha9's IDs misstates a different signal and warmup even though both
have W+1 support. Reusing Alpha4's IDs also misstates its W dependence. Changing
old IDs would relabel historical evidence. Coupling runtime adoption would merge
reader compatibility and scientific execution without separate review. Choose
reader-first attribution. Before producer adoption, reverse only these reader
branches. After any adoption retain historical readers and all generated records.

## Verification

Observe backend/client/rendered RED before source edits. Cover measured/no-fold,
all cross-method/rule/lag/family/finalist/scalar forgeries, mixed v1-v5 stores/API/
client, immutable/unchecked reconstruction, common requests and WF binding.
Hypothesis covers allocated lag coverage. Retain actual unsupported production,
exact producer ASTs and old tests; preserve three complete frozen synthetic
primary/WF/gate/accounting/PCV payloads except UUID/time, unrelated tracked blobs
and search/gate hashes. Independent research/frontend review and foreground
make check-all precede explicit-path individual commit, safe fresh sync,
immediate HEAD:master push and exact CI. No runtime support follows from parsing.

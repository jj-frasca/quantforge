# ADR-352: Prepare attributed Alpha4 purged readers

- **Status:** Accepted
- **Date:** 2026-10-23
- **Deciders:** Codex autonomous session22, ISO2026-W43
- **Extends:** ADR-325/347/349/351
- **Related:** FINDING-265/272

## Context

ADR-351's stable Alpha4 factory is individually published and exact master CI
green. Source and bounded public-portfolio controls support prospective D=W,
shipped lags5/9/21. The actual rolling.apply callback counts <= ties fully;
it does not use pandas Rolling.rank. W-1 signals remain NaN. Its reviewed
dependency chain includes NumPy's fresh boolean mean, unlike the extrema-only
high/Alpha9 recipes. A future strict producer must capture NumPy2.5.4 as well
as pandas3.0.6/Cython at actual execution; current HighRuntime cannot do this.
No such producer/runtime decision is adopted here.

## Decision

Install exact method
`restricted-pandas-3.0.6-numpy-2.5.4-cython-alpha4-purged-equal-weight-continuation-v4`
and rule `rolling-alpha4-percentile-v1` in existing backend/API/client readers.
Only measured/no_usable_folds can carry v4, requiring the exact rule and maximum
lag5/9/21. Other methods cannot carry the new rule; v4 cannot carry another rule.
Full source trials bind xs_alpha4, exactly window/quantile parameters, original
nonboolean Integral window5/9/21 after inherited Trial normalization, and maximum
allocated lag >=window. Keep existing count/finite/scalar/embargo/kept geometry,
immutable reconstruction, common requests and attributed WF-bar checks unchanged.
Recognized v1/v2/v3/v4 may coexist; defaults and historical absence remain exact.

Retain the identity through client parsing and render a plain-language
pandas3.0.6 Cython/NumPy2.5.4 window-percentile qualification inside existing fold
evidence. No raw method/rule IDs in product copy. Existing later-training,
whole-sample family choice, continued-config internal costs/no switching policy,
benchmark costs, mean-of-Sharpes and PIT limitations stay. Structural reader
validation cannot certify runtime execution, allocated source replay or provenance.

Do not change stable factory, signal/callback/ranker, support_lag, measurement,
matrix generation/captures or evaluator. Actual Alpha4 remains unsupported_factory.
Do not imply the current support caption includes a new supported producer.
Future adoption requires its own scientific ADR/TDD with explicit NumPy/pandas/
engine domain, per-config saved before/after receipts, actual allocated maximum,
actual kept-fold pairing and independently reviewed endpoint/dependency evidence.
No score, threshold, fingerprint, longitudinal-v14, generated or frozen record
changes and no calibration/cohort/provider measurement are authorized here.

## Alternatives and reversal

Reusing high or Alpha9 IDs misstates the callback and dependency recipe.
Changing all existing IDs needlessly relabels earlier evidence. Coupling runtime
adoption would expand this compatibility slice beyond a completed domain/capture
decision. Choose reader-first attribution, preserving existing producers.
Before producer adoption, remove these reader branches to reverse. After any
future adoption, preserve historical readers and all generated evidence.

## Verification

Observe backend/client/rendered RED before source edits. Cover supported/no-fold,
cross-method/rule/lag/family/finalist/scalar forgeries, full mixed stores/API/client,
immutable/unchecked copies, complete requests and WF binding. Hypothesis covers
allocated lag coverage. Retain actual unsupported producer, exact producer ASTs,
old tests, frozen3FULLsyntheticpayloads except UUID/time, unrelated blobs and
fingerprints. Require independent research/frontend review and foreground full
make check-all before explicit commit, safe fresh sync, individual immediate push
and exact master CI. No runtime support follows from reader compatibility alone.

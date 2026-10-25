# FINDING-311: Native momentum shift-count addition can read future prices

- **Status:** Corrected by ADR-370
- **Date:** 2026-10-25, Codex autonomous session32 (ISO2026-W43)
- **Severity:** High for accepted direct configurations — signal/engine causality
- **Affected:** MomentumStrategy constructor and its summed reference shift
- **Related:** ADR-314 / FINDING-264 (separate cross-sectional guard)

## Evidence

The longitudinal MomentumStrategy checks lookback>=1 and skip>=0 but retains
the original scalars. Positive np.int8(127) and np.int8(2) satisfy those checks.
Their native sum wraps to-127 in close.shift(skip+lookback), reading a future
reference while the recent-price shift2 remains measurable. A one-bar execution
lag cannot repair a signal that already reads127 future rows.

Parent deterministic witness:300 positive closes100+.01*i on a UTC calendar.
Change only future row137 from101.37 to100. The accepted configuration changes
signal row10 from-1 to+1, and the actual default-cost BacktestEngine's net
return at row11 from-9.990009990024085e-05 to-0.0019000999000997592. Both engine
runs complete with finite positive equity. Native addition warns under over=warn
and is silent under over=ignore; over=raise refuses through FloatingPointError.
An initial much larger future-price perturbation was refused by the engine's
wealth guard and is not the successful engine witness above.

Independent review confirmed earlier signal and actual engine-return changes
on monotone and nonmonotone fixed frames when only rows>=200 were halved.
Python-int127/2 controls preserve their complete earlier prefixes. Unsigned
np.uint8(255)+np.uint8(2) instead wraps to1 rather than257, changing298 signals;
that demonstrates a wrong trailing window, not a future-read claim.

Scratch proof and contract review:
`/tmp/qf-w43-s32-momentum-wrap-prospective.{py,json,md}`.
These are direct-constructor synthetic witnesses, not a real search, measured
false graduate, affected calibration or production occurrence. Current catalog
grids use Python ints; the API MomentumConfig also normalizes these NumPy
inputs to Python ints. Existing cross-sectional ADR-314 does not cover this
longitudinal constructor. Other longitudinal direct shifts do not share this
particular addition of two retained period counts.

## Correction and limits

Validate original positive lookback and nonnegative skip as nonboolean Integral
scalars using existing require_trial_count, then normalize to Python int before
storage and period addition. Reject fractions, floats, booleans and coercible
objects rather than truncating them. Preserve bound meanings, parameter names,
defaults, signature and all signal/engine formulas. Shared-helper error wording
changes deliberately; existing negative/zero tests require the parameter name.

Accepted NumPy counts intentionally change stored scalar type. Safe numerical
parameter values/signals/engine payloads remain bounded compatibility controls,
not original scalar-object identity. Very large Python counts may still refuse
in pandas; no arbitrary-sized indexer or post-construction attribute-mutation
protection is adopted. API/factory coercion policies and other strategies stay.
No threshold, default search/accounting-v14 fingerprint, generated record or
frozen cohort changes. ADR-370 records the prospective decision before TDD.

## Verification

The final prepatch run observed38 failures and11 passing controls, including
separate Hypothesis failures for signal and actual engine net-return prefixes.
After the narrow constructor patch, all49 new/existing momentum tests passed;
the expanded engine/budget/momentum suite passed263tests. Independent final
research review approved all five paths and reran all49tests successfully.
Coverage includes original count domains, signed/unsigned wrap, all three NumPy
overflow policies, zero skip and constructor-only huge exact integral counts.

Parent and independent replays preserve96 safe prepatch numerical parameter,
signal/index/dtype and complete public-engine payloads across three fixed paths
and four original integer families. The whole module AST differs only by the
agreed helper import and constructor replacement. Accepted stored NumPy scalar
types intentionally change to Python int. Both default full-catalog coarse and
refined search fingerprints remain exactly dabe2f579567d64a74761409f8234d8d57b4c107e85f1eaf0c7ffad087739a3d
and edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459.
These bounded matches do not certify arbitrary mutated strategies or every
pandas indexer. Receipts: `/tmp/qf-w43-s32-momentum-count-red-final.log`,
`/tmp/qf-w43-s32-momentum-focused.log`, and
`/tmp/qf-w43-s32-momentum-preservation.log`.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed14810 backend tests
and746 frontend tests, with97.42% backend and97.88% frontend statement coverage;
lint, formatting and strict typing passed. Full receipt:
`/tmp/qf-w43-s32-check370.log`. No threshold, default fingerprint, generated
record or frozen source changed.

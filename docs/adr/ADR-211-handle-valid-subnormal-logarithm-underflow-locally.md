# ADR-211: Handle valid subnormal logarithm underflow locally

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 15, ISO 2026-W41
- **Resolves:** FINDING-153
- **Extends:** ADR-110, ADR-186, ADR-208

## Context

Exact CI e427cd0e rejects valid subnormal return paths because Linux log1p emits
underflow under a strict ambient policy. macOS local gates do not emit the same
signal. The failure precedes the corrected annualized-volatility calculation.
F153 records the three exact unchanged regression cases.

## Decision

After finite and returns > -1 checks, wrap only np.log1p in local
np.errstate(under="ignore"). Return its original rounded logarithms unchanged.
Keep other error modes and all finite-positive wealth/output checks unchanged;
restore caller state automatically. A valid subnormal logarithm is not evidence
of insolvency. This is a platform-signal correction, not a new estimator or an
assertion that every compounded metric preserves arbitrary tiny precision.

No source validation, formula, threshold, calibration identity v10, generated
record, workflow dispatch or paid resource changes. Default-state calibration
already uses underflow-ignore and its measured results remain attributable.

## Verification

Portable RED tests wrap the real log1p with actual NumPy underflow before
delegation, reproducing the strict-platform signal without weakening tests.
Verify exact-float Decimal800 ln(1+r) outputs for subnormal samples, public
metrics integration, invalid-source/wealth rejection before the ufunc, and
caller error-state restoration. Preserve original ADR-208 cases unchanged.
Independent research review, full foreground make check-all, immediate repair
push and exact master CI verification are required.

## Delivery grouping

Owned ADR-210 RED tests were already present when CI failed. Finish its separate
descriptive recovery correction alongside this narrow platform repair; do not
remove or skip owned tests to produce a green repair. Both numerical boundaries
ship in one followup with explicit findings and decisions.

## Reversal

Remove the local underflow policy. This reopens F153's platform-dependent failure.

# FINDING-255: Gate accepts malformed original holdout bundles

- **Date:** 2026-10-16
- **Status:** Resolved — ADR-301
- **Area:** GraduationGate.evaluate original HoldoutScore evidence

## Reproduction and scope

With a finite manual ValidationReport (observed 1, margin 0.5, PBO 0.1,
stability 0.8), years 12 and trials 100, public gate calls pass for each:

| sharpe | total_return | n_bars | benchmark Sharpe | defect |
|---|---|---|---|---|
| 1 | 0.1 | 252 | -infinity | impossible benchmark passes strict comparison |
| True | 0.1 | 252 | 0 | original boolean score coerces to float 1 |
| 1 | 0.1 | True | 0 | original boolean history coerces to int 1 |
| 1 | 0.1 | 252.0 | 0 | original float history coerces to int 252 |
| 1 | NaN | 252 | 0 | malformed return is unused by verdict |
| 1 | -2 | 252 | 0 | wealth-invalid return is unused by verdict |

Fresh parent reproduction: `/tmp/qf-w42-s23-holdout-original-probe.json`;
all six pass at revision `04d49256`. Independent earlier research review reproduced
these standalone defects. No data, search or network input was used.

GateResult persists only holdout Sharpe/history, so it cannot validate missing
benchmark/return evidence and loses some original source types through coercion.
Graduate rejects invalid return downstream; the return examples do not establish
bypassing that durable boundary. This is not a production nonfinite-output,
actual market false-graduate or changed calibration-rate claim.

## Correction and limits

ADR-301 validates the complete original bundle after report/count/duration checks
and before predicates, including inactive benchmark evidence. Original positive
Integral history normalizes locally to Python int; three original finite real
nonboolean score/return values retain native operands and return must exceed -1.
Disabled benchmark comparison remains disabled for valid evidence.

No construction, serialized field, estimator, threshold, config hash, search/v14,
calibration or generated-record change. The guard establishes scalar validity,
not actual history length or matching benchmark provenance. FINDING-256 separately
qualifies float projection; no universal predicate-replay claim is made.

## Verification

Actual preimplementation RED: 80 failing cases/32 preserved controls in 2.75s,
`/tmp/qf-w42-s23-holdout-red.log`. After the narrow guard, 221 focused tests
passed in 3.02s, including 112 new original-evidence, precedence, finite-native,
wealth/Fraction and Hypothesis predicate cases. Ruff lint/format and strict
mypy passed. Parent review inspected the actual RED and final source/tests.

An independent parent check exactly reproduced all 288 pre-change valid public
gate outcomes, including reasons, fields and configuration hashes; AST comparison
proved the complete source unchanged outside the guard and local count projection.
Receipt: `/tmp/qf-w42-s23-holdout-source-baseline-audit.json`. Baseline SHA256:
`7cba1affa34527c46d690bf39781776408bc261afd182bd75fb607b89d0cd8d3`.
No generated-data edit occurred. Separate original/projection control reproduced
FINDING-256 and remains unchanged by this guard.

Foreground `make check-all PYTEST_WORKERS=8` completed green: 12,135 backend
tests, 97.40% backend coverage; 381 frontend tests, 97.66% frontend statements.
All lint, format and type checks passed. Log: `/tmp/qf-w42-s23-check301.log`.
No production code changed after focused GREEN; subsequent edits added docs
and verification receipts only.

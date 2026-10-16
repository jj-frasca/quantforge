# FINDING-250: Infinite available history can pass MinTRL

- **Date:** 2026-10-16
- **Status:** Resolved — ADR-296
- **Area:** GraduationGate.evaluate original track_record_years

## Reproduction and significance

At pre-fix40dfbbfa, a manual ValidationReport with observed Sharpe1, margin.5,
PBO.1, stability.8 and zero diagnostic counts, plus HoldoutScore(1,.1,252,.2),
GateConfig() and100 trials requires9.210340371976184 years. Passing
track_record_years=inf produces mintrl_ok=True and passed=True. All other
components pass by construction; finite history of.5 years fails MinTRL.
An independent research-expert fixture atN2 reproduces the same finite-versus-
infinite verdict change. Zero-dimensional np.array(2.) also passes atN2.

The evaluator accepts booleans as numeric durations, emits a normal failed verdict
for NaN/negative history, and raises incidental type errors for other malformed
values. These are invalid available-history claims, distinct from ADR-015's valid
infinite *required* history for a nonpositive observed Sharpe.

This is direct synthetic public-boundary evidence. It does not establish production
misuse, stored corruption, a market false graduate or a revised calibration rate.
No source, provider, broker, real experiment search or frozen cohort is used.

## Governed correction

ADR-296 requires original finite float-representable nonboolean Real, original
nonnegativity and ValueError refusal. Preserve the native comparison operand and
existing report/count precedence. Zero history remains valid; atN1 a positive
Sharpe has requirement zero, so zero available history still clears that component.
Finite available history never satisfies an infinite requirement.

No validation threshold, estimator, reason, config hash, accounting-v14 identity,
JSON schema, generated artifact or historical cohort changes. This does not certify
duration provenance or correct the separate standalone MinBTL scalar/arithmetic gaps.

## Verification

Actual pre-implementation regression run:57 failed/23 preserved in3.40s
(`/tmp/qf-w42-s21-duration-red.log`). After the evaluator guard,239 affected tests
passed; independent research-expert verification passed230 tests and approved all
six paths. Original Fraction threshold comparisons, invalid count/report precedence,
zero history and infinite required history were retained. Parent AST comparison
confirmed only the Real import and duration guard changed executable gate source
(`/tmp/qf-w42-s21-source296.json`).

Foreground `make check-all PYTEST_WORKERS=8` completed successfully:
11,631 backend tests,97.38% coverage;381 frontend tests,97.66% statement coverage;
Ruff lint/format, mypy184 files, ESLint and TypeScript all green.
Receipt:`/tmp/qf-w42-s21-check296.log`. Exact master CI is checked after individual
push; no generated records or frozen sources/checkpoints were authored.

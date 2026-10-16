# FINDING-251: Standalone MinBTL accepts invalid observed Sharpe

- **Date:** 2026-10-16
- **Status:** Resolved — ADR-297
- **Area:** minbtl_years original annualized_sharpe

## Evidence and significance

At `f30370ee`, direct minbtl_years(100, score) returns NaN for NaN, zero for positive
infinity,9.210340371976184 for True and infinity for False/negative infinity.
NumPy 0-D scalar arrays also reach arithmetic. Original invalid score evidence
therefore becomes a numerical requirement instead of a deliberate input refusal.
Independent research-expert probes confirmed the NaN/infinity/boolean/array cases.

This is standalone synthetic API evidence. GraduationGate reconstructs its
ValidationReport first and receives finite Python-float observed Sharpe; no
production false graduate, corrupt generated record or revised rate is established.
No search, provider, broker, source generation or cohort replay was used.

## Governed correction and limits

ADR-297 validates original finite float-representable nonboolean Real after trial
count and before the nonpositive shortcut. Preserve original operand, sign, square
and division; no numeric normalization, recovery or threshold change. Zero and
negative finite scores still require infinite history. Count errors retain precedence,
and N=1 must not excuse malformed score evidence.

FINDING-252 separately records finite arithmetic faults. This guard does not make
all finite input computable, fix integer square wrap or certify numerical precision.
Production procedure, config/search hashes, accounting v14, schemas, data and frozen
historical/cohort evidence remain unchanged.

## Verification

Actual pre-implementation test run: 63 failures and 37 preserved controls in
2.19 seconds (`/tmp/qf-w42-s21-minbtl-red.log`). After the guard, all 339 affected
tests passed; independent research review reran all 339 and approved the complete
seven-path slice. Existing financial Hypothesis properties remain unchanged.
Parent AST verification confirmed only the original score guard and named MinBTL
docstring changed gate source (`/tmp/qf-w42-s21-source297.json`).

Foreground `make check-all PYTEST_WORKERS=8` completed successfully: 11,731 backend
tests, 97.38% coverage; 381 frontend tests, 97.66% statement coverage. All lint,
format and type checks passed. Receipt: `/tmp/qf-w42-s21-check297.log`.
Exact master CI is checked after individual push. FINDING-252 remains Open;
no generated records or frozen sources/checkpoints were authored.

# FINDING-304: No-forward shortcuts bypass source calendar identity

- **Status:** Corrected by ADR-364
- **Date:** 2026-10-24
- **Severity:** Medium — malformed direct source evidence becomes a hold or zero score
- **Scope:** `score_forward`, `evaluate_cross_sectional_lifecycle`, `evaluate_lifecycle`
- **Prior art:** ADR-168, ADR-176, ADR-255, ADR-363

## Evidence and limits

All three raw-data wrappers check for forward dates before invoking their return
engines. With all source dates before the freeze boundary, they bypass the
engines' unique ascending calendar checks and publish a zero score or hold from
an invalid original calendar.

Independent deterministic witness: freeze2026-01-05 UTC, two rows of price100.
Use either descending dates January3/January2 or duplicate dates January2/January2.
The panel has columns A/B and a matching frozen momentum position with
lookback1/skip0/quantile0.5/cost0.001. The single-name frame has `close` and an A
momentum position with lookback1. Both use ordinary default lifecycle policies.
`score_forward` emits zero bars, zero statistics and the maximum source date as
`as_of`. Both lifecycle wrappers hold. In contrast, `asset_returns` and
`BacktestEngine.run` on those same calendars reject them. Ordered January2/January3
controls are accepted by all five entry points.

This establishes malformed direct source acceptance, not a noncausal measured
return: no return calculation occurs in these bypass branches. No actual managed
decision, corrupted generated book, affected graduate or false graduation is
established. Production `ResearchDataset` already protects chronology. The
single-name score producer requires that checked dataset and is outside this
raw-wrapper correction.

ADR-176/255 explicitly placed guards at engine boundaries; ADR-168 placed paired
return checks at pure lifecycle boundaries and policy checks at wrappers. This
is a separate extension to wrapper source identity, not a claim those earlier
decisions explicitly required all source validation before every shortcut.

## Correction and verification

Check native original index uniqueness and ascending order before wrapper calendar
access or no-forward shortcuts. Preserve policy validation first, frozen panel
columns next where applicable, and the scorer's existing optional-evidence
reconstruction and frozen-symbol checks before calendar validation. Score-root
common-revision checks remain later as before. Reuse existing engine-family error messages. Do not
sort, deduplicate, coerce, call the engine merely to validate, require UTC or daily
cadence, or add price/configuration validation.

Preserve existing valid-domain differences: empty and naive lifecycle calls can
hold; empty/naive panel scores already fail aware-`as_of` validation. Generic
object indexes of aware timestamp objects are supported; integer calendar cutoff
comparisons already fail. This guard adds no support for them. NaT-containing
indexes fail the same native ordering predicate as the engines.

Twelve regressions failed before implementation while29 controls passed. After
adding only the three two-line native guards, all332 focused tests pass, including
41 new tests and Hypothesis source-date order checks. Independent final research
review approves all six paths, independently passes the41 tests, and exactly
reproduces603 prepatch outputs:600 successful scores/decisions and three existing
scorer failures for empty/naive inputs. The bounded controls cover four panel
factors, zero/grace/measured windows, two costs, complete/partial static maps,
oscillating/tied prices, UTC/offset/object-timestamp calendars and single-name
momentum, with unchanged caller inputs. Removing only the three calendar guards
restores both complete prior module ASTs. This does not certify arbitrary
floating-point behavior or source provenance.

Full foreground `make check-all PYTEST_WORKERS=2` passes:14,639 backend and746
frontend tests,97.41% and97.88% statement coverage respectively, lint, format and
strict typing. Thresholds, policy hashes, schemas, accounting-v14 and all generated
or frozen records remain unchanged.

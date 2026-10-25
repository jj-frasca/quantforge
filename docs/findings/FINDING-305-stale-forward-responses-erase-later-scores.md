# FINDING-305: Stale forward responses erase later scores

- **Status:** Corrected by ADR-365
- **Date:** 2026-10-24
- **Severity:** High — later observed forward evidence can be replaced by an older window
- **Scope:** Managed single-name and cross-sectional forward updates
- **Prior art:** ADR-019/020/025/139/140/148/149/166

## Evidence

Both managers replace an open position's score with every successfully computed
candidate, without comparing its observation cutoff to the retained score.
Quality validation and requested-range membership do not ensure that a response
contains the latest previously observed dates. A truncated response can therefore
erase accrued observations and evaluate lifecycle on an older window.

Independent witness uses the real `prepare_research_dataset` quality pipeline on
synthetic canonical `PriceBar` objects. A/B have510 business-day observations
starting2024-01-01 UTC. At row i, prices are100+i/100 for A and100-i/100 for B,
with OHLC equal, volume100, adjustment1 and source yfinance. Both the510-row
full response and its504-row prefix use the same requested end2025-12-16 UTC,
same start, adapter revision and executed code identity. Every actual quality
report passes; no fabricated passed report is needed. The prefix also satisfies
the panel builder's504-observation minimum and preserves the exact universe.

Freeze at row505. First manage the full response, then manage the retained open
position with the stale prefix and the same `now`. For a value factor with
A1/B0, quantile0.5 and cost0.001, the retained score initially has cutoff
2025-12-12, four forward bars/curve points and return0.0008022988952240961.
The stale update replaces it with cutoff2025-12-04, zero bars/points and return0.
Single-name A momentum lookback3/skip0 likewise replaces a four-bar score with
return0.00038077106139944306 by the earlier zero-bar score. Both positions stay
open under unchanged default grace policies.

These are quality-checked synthetic managed-path reproductions, not evidence of
an actual vendor response, corrupted generated book, affected graduate, broker
order, or false graduation. No calibration or search was run. Current ADRs bind
intrinsic score and dataset identity but do not explicitly require monotonic
retained cutoffs; the correction is a new retention contract extension.

## Correction and verification

After computing a valid candidate score, if an existing score has a later
`as_of`, retain the entire original position and continue before lifecycle
evaluation. Apply the same rule in both managers. Do not merge curves, invent
bars, compare against `now`, change quality thresholds, or add a monotonic
bar-count requirement. Equal-cutoff recomputations remain possible for revised
history, and first/newer scores keep their existing behavior. Closed/retired
positions remain untouched. An intentional removal of previously observed later
dates needs an explicit correction process rather than an automatic stale refresh.

Eight regressions failed before implementation while eight controls passed.
The two three-line manager guards then pass178 focused tests, including16 new
tests and a Hypothesis checked-response order invariant. Real quality-prepared
fixtures exercise stale retention, complete original-position identity, lifecycle
deferral, equal-cutoff corrections, newer/first scores, terminal positions and
legacy absent evidence/empty curves.

Independent final research review approves all six paths, independently passes
the16 new tests and reproduces136 complete prepatch managed-position outputs
exactly across first/equal/newer candidates, both managers, oscillating/tied
paths, grace/hold/exit/retire policies and legacy evidence states. Caller positions
and provider frames remain unchanged. Removing only the two guards restores
the three reviewed source-module ASTs; `paper.py` is also byte-identical.
These bounded controls do not certify arbitrary source provenance or arithmetic.

Full foreground `make check-all PYTEST_WORKERS=2` passes:14,655 backend and746
frontend tests,97.41% and97.88% statement coverage respectively, lint, format and
strict typing. No threshold, policy hash, schema, accounting-v14, generated record
or frozen cohort changes.

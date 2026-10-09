# FINDING-176: Null holdout maximum can contradict its graduate list

- **Date:** 2026-10-09
- **Severity:** Medium — durable graduate summary can be false
- **Status:** Corrected by ADR-226
- **Affected:** NullCalibration construction and merge input validation

## Evidence

Before ADR-226, the modern iid 7,400-bar artifact accepts max_holdout_sharpe=10
with no graduates. A valid typed legacy graduate with holdout Sharpe 2 accepts
max_holdout_sharpe=None. Both are accepted on construction. Single-shard merge
accepts each input and silently normalizes its maximum to None or 2 respectively;
it does not retain the contradiction, but it also does not report it.

Native calibrate_gate, merge_calibrations and CLI wording define the field as
maximum holdout Sharpe among graduates. Nonpassing joint finalists do not belong
in this maximum. The required graduate list supplies this evidence even without
modern joints. All eight committed artifacts have empty graduate lists and None
maxima; no corrupt committed record or changed candidate result was observed.

## Correction boundary

Require the exact graduate-list maximum, or None when empty, at root validation.
Keep signed scores and ordering. Do not equate trial-wide max_deflated_sharpe with
selected graduate margins. ADR-226 does not change displayed deflation-bar policy,
thresholds, estimators, fingerprints, producers, sources or generated data.

## Correction and verification

Root validation now refuses a maximum different from its graduate list, including
legacy artifacts. Authoritative merge reconstruction inherits the refusal.
TDD observed 18 failures and six preserved cases before the five-line guard.
The broad affected run passed 631 cases and identified two contradictory legacy
fixtures. Their omitted-graduate mutation now sets the matching None maximum;
the original hostile joint omission and rejection assertions remain intact.
The original bounds-test fixture now also reports its actual graduate maximum,
so rejecting its original probability beyond one cannot be masked by this guard.
Independent review passed 55 cases, including all 24 new cases and four native
producer/merge checks. All eight artifacts round-trip and merge unchanged.
Final focused verification passed 112 cases. The first full gate identified
three API fixtures that reported 0.85 with no graduates; their helper now reports
None for that case, preserving all endpoint assertions. All 18 integration cases
passed after this correction. Fresh foreground `make check-all` passed 3,801
backend and 363 frontend tests, including lint, typing and coverage.

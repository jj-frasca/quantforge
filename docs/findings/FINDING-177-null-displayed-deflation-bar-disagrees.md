# FINDING-177: Null displayed deflation bar can contradict searched histories

- **Date:** 2026-10-09
- **Severity:** Medium — reported selection benchmark can be false
- **Status:** Corrected by ADR-227
- **Affected:** NullCalibration reported deflation_bar

## Evidence

The modern iid 7,400-bar N=200 artifact accepts deflation_bar=0 with its complete
200-element searched holdout-year list unchanged. Native production and merge
compute the displayed bar as expected_max_sharpe_under_null(N, median(years)),
which gives 1.3432393159670402 for this artifact. Single-shard merge accepts the
contradictory input and silently normalizes the bar. The claim is false on direct
construction even though merge does not retain it.

All eight committed artifacts have 200 searched histories and exactly match the
native formula: bars 1.5724338155830546 at 5,400 total bars, 1.4825048186210867 at
6,075, 1.3432393159670402 at 7,400 and 1.2017546106680337 at 9,247. No corrupt
committed record was observed. ADR-224 survivor accounting uses each canonical
graduate's own holdout history, so this reporting gap does not change that repair.

Independent arithmetic review also reproduced `median([1e308, 1e308]) == inf`,
which sends the existing formula to a false zero despite finite positive inputs.
Two histories of `1e-320` years yield an infinite expected bar. Complete-history
reconciliation must refuse nonfinite derived evidence as well as false finite
claims, without changing the formula or inventing a replacement measurement.

## Proposed boundary

When searched holdout_years is complete, bind the displayed bar to the existing
formula at enclosing N and median searched years. Preserve incomplete or empty
legacy histories without inventing evidence or requiring new list lengths.
Changing the approximation, individual survival history, thresholds, trial-wide
maximum DSR, fingerprints, sources or generated data is outside this finding.
ADR-226 addresses only the separate graduate maximum. ADR-227 decides this
conditional history relationship and nonfinite-derived-evidence refusal.

## Correction and verification

Root validation now requires the unchanged displayed-bar formula when searched
histories are complete, with finite positive derived median and finite bar.
Authoritative merge reconstructs and refuses bad input before normalization.
Incomplete and empty legacy histories remain valid without an inferred relation.
Individual survivor calculations and power fields retain their prior meanings.

TDD observed 23 failures and nine preserved cases before the eight-line guard.
Tiny-year unchecked merge already rejected its nonfinite output before this fix;
the new guard additionally rejects the input, rather than claiming that case was
previously accepted end-to-end. All 32 new tests pass. Independent review passed
63 cases, including own-history survivor and four native producer/merge checks;
all eight committed artifacts round-trip and merge unchanged. The broad affected
run passed 642 cases and found a shared pool-report fixture responsible for 41
failures. That fixture now computes its actual N/history bar. Other synthetic
null fixture bars were corrected without changing power siblings, original
hostile inputs or rejection assertions. All 101 pool-report cases passed after
the shared correction. Full foreground `make check-all` passed 3,833 backend
and 363 frontend tests, including lint, typing and coverage.

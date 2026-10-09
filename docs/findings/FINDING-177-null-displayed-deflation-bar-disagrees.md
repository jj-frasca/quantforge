# FINDING-177: Null displayed deflation bar can contradict searched histories

- **Date:** 2026-10-09
- **Severity:** Medium — reported selection benchmark can be false
- **Status:** Open; separate correction required
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

## Proposed boundary

When searched holdout_years is complete, bind the displayed bar to the existing
formula at enclosing N and median searched years. Preserve incomplete or empty
legacy histories without inventing evidence or requiring new list lengths.
Changing the approximation, individual survival history, thresholds, trial-wide
maximum DSR, fingerprints, sources or generated data is outside this finding.
ADR-226 addresses only the separate graduate maximum and leaves this gap open.

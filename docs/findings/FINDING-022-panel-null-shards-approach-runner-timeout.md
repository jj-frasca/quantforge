# FINDING-022: Panel-null shards approach the runner timeout before slowdown

- **Severity:** High — the one-shot measurement can lose complete shards at the six-hour job limit
- **Found:** 2026-09-12 by Codex hostile review of ADR-081 execution feasibility
- **Status:** Resolved by ADR-086
- **Affected:** `panel-null-calibration.yml`

## Finding

ADR-081 assigns ten complete 39-symbol panels to each batch job. Every symbol in every panel runs
the full production search, so a shard performs 390 serial searches. The job timeout is 360 minutes,
GitHub's maximum ordinary job duration. This topology leaves too little margin for runner slowdown,
setup, serialization, or a slow strategy family and can make the fixed 400-panel measurement fail
after substantial work even when every search is correct.

## Evidence

The frozen eligible cohort contains 39 symbols and the production candidate allocator evaluates 200
configurations per search. A local representative production search over 7,400 synthetic daily bars
took 44.78 seconds wall clock. At that observed rate, one current shard needs about 291 minutes for
its 390 searches before runner differences and workflow overhead. By comparison, the established
independent-null workflow gives a 300-minute timeout to only 25 searches per job; the panel shard
attempts 15.6 times that search count with only 1.2 times the deadline.

The measurement has not been dispatched, so no panel result or generated artifact is affected.

## Impact

A timeout omits the shard artifact. Consolidation correctly refuses an incomplete global-index set,
but the manual one-look measurement would still have consumed many runner-hours without producing
its pre-registered inference. Raising the timeout cannot solve the problem because 360 minutes is
already the platform ceiling.

## Required correction

Keep every panel indivisible and preserve global indices 0 through 399, but reduce each shard from
ten panels to four. One job then performs 156 searches; 100 disjoint shards still reproduce exactly
the same seeded 400-panel measurement. Keep bounded concurrency and the existing fail-closed
consolidation.

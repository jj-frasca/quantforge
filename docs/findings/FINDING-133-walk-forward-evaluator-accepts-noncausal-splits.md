# FINDING-133: Walk-forward evaluation accepts noncausal splits

- **Date:** 2026-10-07
- **Severity:** Medium — direct split callers can publish a causal diagnostic using future data
- **Status:** Resolved — ADR-197

## Evidence

For a four-row two-config return matrix with first-column returns `.01, .02,
.03, .04` and their negatives in the second column, `walk_forward_evaluate`
accepts train rows `[2,3]` and test rows `[0,1]`, selecting config zero on future
data and publishing OOS Sharpe approximately 33.67491648. It also accepts
train `[0,1]` and test `[1,2]`, reusing a test observation for selection.
Train `[-2,-1]` with test `[0,1]` passes the existing upper-bound check and
NumPy aliases those negative indices to the last two future rows.

The ordinary production split generator is causal; this finding identifies the
public evaluator's unchecked caller boundary, not a demonstrated production leak
or false graduate. Result-model finite/count checks cannot recover row identity.
Walk-forward remains diagnostic and no gate threshold is implicated.

## Correction and limits

Before selecting in each split, require nonempty one-dimensional integer row
arrays, nonnegative in-range rows, unique ascending order, and `max(train) <
min(test)`. Reject malformed geometry without sorting, deduplicating, clamping
or rebuilding it. Preserve generated expanding splits, earlier test rows entering
later train blocks, singleton blocks, temporal gaps, score arithmetic and paired
benchmark rows. Matrix return-evidence validity is a separate boundary.

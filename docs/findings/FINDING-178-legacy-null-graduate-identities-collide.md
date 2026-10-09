# FINDING-178: Legacy null graduate identities can collide

- **Date:** 2026-10-09
- **Severity:** Medium — ambiguous identities counted as distinct symbols
- **Status:** Corrected by ADR-228
- **Affected:** Legacy NullCalibration graduate lists and shard merge

## Evidence

A coherent legacy root with N=2, two graduates, rate=1, two survivors, a truthful
N/history bar and maximum Sharpe 2 accepts graduate symbols [A, A]. Single-shard
merge retains this claim exactly. Two individually valid legacy N=1 shards each
naming graduate A merge into N=2 and two graduates with that same label.

A repeated label establishes ambiguous recorded symbol identity, not proof that
underlying RNG paths are identical. It cannot safely support a distinct-symbol
claim without additional evidence. Native calibrate_gate accepts a unique-key
source mapping; the shard driver names symbols by global index and uses that
index for its seed (ADR-037). No producer collision was observed. All eight
committed artifacts have empty graduate lists and no collisions. Modern paired
searched identities already refuse duplicate symbols; this gap is legacy-specific.

## Correction boundary

Require unique symbols in the required graduate list even without joints.
Authoritative merge input reconstruction and merged-root validation inherit the
guard. Preserve absent joints and unknown nongraduate identities; do not infer,
deduplicate, namespace, rewrite N/counts or claim independence from distinct names.
No threshold, survivor estimator, fingerprint, producer, source or data change.

## Correction and verification

The root now refuses repeated known graduate symbols regardless of joint
availability. Authoritative reconstruction and the merged root inherit refusal,
including cross-shard ambiguity. No recorded identity or count is repaired.

TDD observed 13 failures and five preserved cases before the three-line guard.
All 454 affected consumer/API cases passed. Independent review passed 22 cases:
all 18 new cases, the existing modern duplicate check and three native legacy
combined-N/survival merge checks. All eight committed artifacts round-trip and
merge unchanged; only the NullCalibration definition changed in production.
Full foreground `make check-all` passed 3,851 backend and 363 frontend tests,
including lint, typing and coverage.

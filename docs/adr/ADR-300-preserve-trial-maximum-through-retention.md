# ADR-300: Preserve trial-count maxima through retention

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 21, ISO 2026-W42
- **Resolves:** FINDING-254
- **Extends:** ADR-026/032/046/062/066/299

## Context

The store/report prior is the maximum lifetime counter, but retain_recent keeps
only graduates and the newest N nongraduates. ADR-066 already recognizes that
newest need not mean largest because of legacy resets or clock skew. Seven valid,
distinct nongraduate records with chronological lifetimes [100,4,4,4,4,4,4] each
covering four evaluations lose their maximum under latest-five retention: prior
100 becomes4. ADR-299's local accounting bounds correctly accept every row.

A read-only audit of the current 607 committed symbol partitions found no present
maximum loss under quota5; all 3,294 current rows remain retained. This does not
reconstruct deleted history or establish historical production corruption.

## Options considered

1. Keep one original maximum-count witness only when necessary: preserves the
   prior and bounded storage; may retain one extra older nongraduate per symbol.
2. Keep newest N only: smallest existing footprint but can silently lower the
   DSR/MinTRL denominator despite valid individual records.
3. Rewrite a retained row with the discarded maximum: avoids an extra row but
   fabricates that experiment's original accounting claim. Rejected.
4. Persist a separate high-water counter: possible, but adds schema, transport and
   writer coordination when an existing immutable record already supplies evidence.

## Decision

Retain all graduates and the newest N nongraduates per symbol in their existing
order. Compare their maximum counter (or default0) with the original maximum.
Append one original nongraduate witness only when its count would otherwise be
lost. Choose the first original maximum on ties, deterministic for the supplied
input order. A graduate or recent row already representing that maximum needs no
extra witness. At quota0, preserve a positive maximum; zero-only nongraduates can
be dropped because the prior remains0. Preserve original records, values and
existing policy output order; do not synthesize a counter, UUID, timestamp or trial.

There are at most N+1 nongraduates per symbol, plus all graduates. When no witness
is necessary the output is exactly the prior policy's result. Accept the bounded
storage and extra linear scan beside existing sorting. The quota describes recent
nongraduates, with a required count witness in addition when necessary.

Require original nonnegative nonboolean Integral quota at both public helper and
partitioned-store construction, using require_trial_count and Python-int
normalization. Reject negative, boolean, None, float and other coercible inputs
before source iteration or filesystem access. Preserve migration's explicit
lossless None-to-input-count conversion before it constructs the store; no quota
cap or migration rewrite is introduced.

No max aggregation, deduplication, search formula, threshold, accounting-v14,
calibration or generated-record change. This protects pruning of canonical
records, not arbitrary unchecked mutation, contradictory same-UUID replacement
or reconstruction of prior discarded evidence. Calibration does not use this
persistent store; no rate is remeasured or inferred.

## Consequences, verification and reversal

Retention cannot lower any represented per-symbol prior. Test nonmonotone counts,
clock skew, mixed symbols, graduate-held maxima, quota0, deterministic ties,
original-object/value/order retention and the N+1 bound. Hypothesis verifies max
preservation for arbitrary valid histories. Exercise actual partition writes only
under pytest scratch paths. Compare both policies on every committed partition
without writing it. Independent review and foreground make check-all precede
individual delivery and exact CI.

Restore latest-N-only retention and permissive quota inputs to reverse, reopening
FINDING-254. Preserve all original source evidence and generated records.

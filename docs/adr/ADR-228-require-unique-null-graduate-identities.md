# ADR-228: Require unique null graduate symbol identities

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 21, ISO 2026-W41
- **Resolves:** FINDING-178
- **Extends:** ADR-036, ADR-037, ADR-080, ADR-224

## Context

Legacy null roots without joints can carry two graduates with the same symbol,
counting the ambiguous identity as two distinct searched symbols. Single-shard
merge retains the claim; two individually valid shards naming the same graduate
also merge into two graduates. Modern complete diagnostic identities already
refuse collisions, but the required graduate list lacks that legacy boundary.
Native source mappings and global-index shard names identify distinct symbols.
All eight committed artifacts are collision-free. Repeated labels alone do not
prove identical RNG draws or a changed measured Type-I result.

## Decision

Require graduate symbols to be unique within every NullCalibration, including
legacy artifacts without joints. Authoritative reconstruction inherits refusal;
the merged root also refuses collisions across otherwise valid shards.

Reject ambiguity rather than deduplicating, rewriting counts or inventing
namespaces. Do not infer identities of missing nongraduates, require modern
joints, compare unrecorded RNG paths or change N, survivor arithmetic, sources,
thresholds, fingerprints, producers, JSON shape or generated data. Preserve
empty graduate lists, distinct symbol order and nullable probabilities.

## Alternatives and limits

A joint-only guard leaves legacy ambiguity intact. Deduplicating cannot establish
whether labels denote one draw or two independent runs with reused names, and
would invent a corrected denominator. Namespacing at merge silently rewrites
recorded identity. The guard does not establish independence of distinct names
or completeness of missing searched identities.

## Verification

Observe direct/JSON/unchecked reconstruction, single- and two-shard collisions
before code. Protect empty and distinct legacy graduates, order and ordinary
combined-N merge, existing modern collision refusals, native producers and all
eight artifacts. Run affected/API tests and the full foreground gate.

## Reversal

Remove the root unique-graduate relationship guard; ambiguous repeated identities
can again be counted as distinct graduates without changing producer arithmetic.

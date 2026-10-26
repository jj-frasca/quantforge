# ADR-379: Refuse nonfinite fundamental snapshots without a missingness fallback

- **Status:** Accepted
- **Date:** 2026-10-26
- **Deciders:** Codex autonomous session 3, ISO2026-W44; research/data review
- **Addresses:** FINDING-320's remaining canonical numeric persistence gap
- **Extends:** ADR-017, ADR-147 and ADR-378

## Context

ADR-378 vetoes enabled nonfinite screen metrics, but FundamentalSnapshot still
accepts nonfinite numbers and serializes them as null. A snapshot-only finite
constructor could instead raise ValidationError into the three hunt wrappers'
ValueError-to-None fallback, removing an existing fundamental veto. Numeric
validity and provider classification must change together. A read-only inventory
of all 2,688 stored snapshots across 607 files/3,301 rows found identical finite-
only validation and canonical JSON, with unchanged source bytes. It cannot recover
historical values already serialized as null or establish vendor truth.

## Options Considered

1. **Finite snapshot construction plus explicit validation-error propagation.**
   - Pro: rejects invalid canonical numeric evidence before serialization while
     keeping it distinct from the existing unavailable-fundamentals fallback.
   - Con: classifies all snapshot ValidationErrors as errors, including malformed
     nonnumeric fields already rejected by the old model; nested readers also refuse.
2. **Finite snapshot construction alone.**
   - Pro: smallest model diff.
   - Con: can convert an existing veto into absent evidence in production wrappers.
3. **Invent a new numeric-only exception and provider-result protocol.**
   - Pro: permits narrower error classification and richer unavailable reasons.
   - Con: larger parser/provider architecture change than this finite model boundary
     needs; raw parser errors and availability provenance require separate decisions.

## Decision

Add allow_inf_nan=False only to FundamentalSnapshot's existing frozen ConfigDict,
covering all six numeric fields while preserving nullable fields, defaults, finite
coercions and JSON shape. In scripts/shard_hunt.py, run_hunt.py and hunt.py, reraising
Pydantic ValidationError precedes the existing ValueError/OSError-to-None catch.
The universe's existing per-symbol handler then records an error before search
rather than turning invalid snapshots into absent fundamentals. Deliberately apply
this classification to every ValidationError, not only numeric failures.

No estimator, screen predicate, threshold, parser arithmetic, history/Annual model,
search, workflow or v14 change. Plain ValueError/OSError fallbacks remain as before,
including missing CIK/no revenue/network failure. This does not classify every raw
parser failure as invalid rather than unavailable. Custom provider fallbacks and
standalone unchecked model copies remain outside the guarantee.

## Consequences

Ordinary construction/JSON loading and the parser's final snapshot return refuse
nonfinite evidence. Existing Experiment reconstruction and store revalidation also
reject invalid nested copies before retaining/writing them. Pool readers propagate
invalid persisted numeric claims rather than silently dropping rows. Current stored
snapshots remain compatible, including nullable missing fields. Historical lost
values cannot be reconstructed and no generated record is rewritten.

Retain ADR-378's consumer defenses with explicitly unchecked numeric snapshots.
Change its parser-overflow regression to require refusal before screening. Observe
new failing direct/JSON, parser, actual-wrapper, universe and nested-writer tests
before implementation; preserve finite snapshots, all three availability fallbacks,
complete source ASTs and frozen pool hashes/JSON. Obtain final independent reviews
and pass foreground make check-all before individual publication. Reverse the model
keyword and the three ValidationError catches together, reopening numeric loss.

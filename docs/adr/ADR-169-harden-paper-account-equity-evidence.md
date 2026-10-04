# ADR-169: Harden paper-account equity evidence

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 28 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-100
- **Extends:** ADR-019, ADR-021, ADR-030, and ADR-141

## Context

The broker account curve is a durable observation ledger, but `EquityPoint` and its writer trust
nonfinite values, ambiguous timestamps, partial benchmark evidence, and unchecked model copies.
Append arithmetic trusts its nominal/inception denominators and prior chronology. All 46 committed
nominal returns match independently; 26 measured alphas use the intentional historical formula,
seven use ADR-141's corrected formula, and 13 are unmeasured. None is unexplained.

## Options Considered

1. **Validate intrinsic points and ordered batches before arithmetic or writing.**
   - Pro: preserves historical observations while rejecting malformed new evidence atomically.
   - Con: adds one linear reconstruction pass and requires aware timestamps.
2. **Recompute every historical scalar from current formulas.**
   - Pro: makes all rows uniformly formula-coherent.
   - Con: rewrites ADR-141's intentional history and loses nominal baseline/benchmark provenance.
3. **Validate only API responses.**
   - Pro: smaller write-path change.
   - Con: invalid bytes can reach the canonical ledger before publication fails.

## Decision

Always revalidate `EquityPoint` instances. Require finite observed/reporting scalars, aware UTC
snapshot timestamps, nonnegative integer position counts, and benchmark/alpha fields either both
absent or both present. Allow finite negative cash and zero/negative observed equity: an account
ledger must not hide margin balances or insolvency by imposing strategy-wealth assumptions.

Reconstruct each point and require strictly increasing snapshot times in complete batches before
append arithmetic, load return, or writer directory creation. Append validates an aware current
instant, finite positive nominal starting equity, and (only when computing measured alpha) a finite
positive inception equity. The newly appended observation must follow prior history. Do not bind
stored scalar returns to a guessed fixed nominal baseline or restate historical alpha formulas.

## Consequences

- Invalid unchecked points, duplicate/reversed dates, undefined denominators, and partial benchmark
  claims fail before a snapshot write can alter the ledger or create its directory.
- Existing JSON shape, nominal custom-baseline behavior, and ADR-141 history remain supported.
- Unmeasured snapshots can honestly record zero/negative account equity; measured alpha requires
  an economically meaningful positive inception denominator.
- No account access, credentials, broker order, generated record, formula, or threshold changes.

## Reversal

Restore permissive points and writer/append boundaries. That reopens FINDING-100 and is not recommended.

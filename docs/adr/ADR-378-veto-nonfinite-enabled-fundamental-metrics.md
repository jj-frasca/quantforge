# ADR-378: Veto nonfinite metrics in enabled fundamental checks

- **Status:** Accepted
- **Date:** 2026-10-26
- **Deciders:** Codex autonomous session 3, ISO2026-W44; research/data review
- **Partially addresses:** FINDING-320
- **Extends:** ADR-017 and ADR-377

## Context

FundamentalSnapshot can carry NaN or infinite growth/margins. Finite synthetic
parser inputs can overflow to infinite growth, which the default screen accepts
before JSON serialization turns it into null. Negative infinity already vetoes.
A finite-only snapshot constructor would raise ValueError-compatible validation
errors that the daily provider converts into absent fundamentals, potentially
removing that existing veto. No actual affected production cohort is established.

## Options Considered

1. **Return explicit failed screens for enabled nonfinite metrics.**
   - Pro: closes the immediate veto gap without adding a provider exception or
     changing deliberate missing-fundamentals admission.
   - Con: durable snapshot numeric evidence and provider fallback remain unresolved.
2. **Require finite snapshot fields at construction only.**
   - Pro: prevents nonfinite claims at that model boundary.
   - Con: existing ValueError-to-None fallback can turn a veto into eligibility;
     invalid and unavailable data need a separately designed error contract.
3. **Redesign parsing, snapshots and every provider fallback together.**
   - Pro: can address numeric persistence and invalid/unavailable semantics fully.
   - Con: changes multiple acquisition boundaries and needs broader compatibility
     evidence; it delays an independently useful, narrow consumer correction.

## Decision

For each enabled screen check, retain its None branch first, then refuse a
nonfinite metric with an explicit reason before the existing native comparison.
Use math.isfinite for the validated float metric. Disabled criteria keep ignoring
their metrics, including nonfinite values. Preserve all finite thresholds, source
metrics, comparisons, defaults, existing missing-value reasons and passed-result
shape. Add no constructor, parser, provider, search, gate or v14 change.

## Consequences

NaN and positive infinity cannot satisfy an enabled fundamental check. Negative
infinity remains failed, with a nonfinite reason replacing its old comparison
reason. No new exception reaches the provider's missing-data fallback. This is
input-evidence validity, not a calibrated graduation threshold or a market-safety
claim. Snapshot serialization can still turn nonfinite values into null; F320
remains open for that loss and the invalid-versus-unavailable source policy.

Write tests and observe failure before source edits for both fields, all three
nonfinite values and actual finite-input parser overflow. Preserve disabled,
finite and None controls, use a Hypothesis refusal invariant and exact finite
replay, obtain independent research/data review and run foreground make check-all.
Reversal removes only the two nonfinite branches and their math import, restoring
the consumer gap without changing any historical record.

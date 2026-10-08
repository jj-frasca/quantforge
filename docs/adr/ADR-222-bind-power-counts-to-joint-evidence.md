# ADR-222: Bind modern power counts to canonical joint evidence

- **Status:** Accepted
- **Date:** 2026-10-08
- **Deciders:** Codex autonomous session 19, ISO 2026-W41
- **Resolves:** FINDING-172
- **Extends:** ADR-018, ADR-049, ADR-102, ADR-103, ADR-218, ADR-221

## Context

Complete joint records and coherent scalar bounds can coexist with contradictory
headline detection, survival and component counts. ADR-102 preserves canonical
incumbent evidence for these very measurements; freezing both stories does not
establish their agreement.

## Decision

When symbol_verdicts is present, after existing completeness, uniqueness and
probability-projection checks, require:

1. n_detected equals the number of incumbent GateResult.passed records;
2. n_clear_deflation_bar equals the incumbent passers whose locked-holdout
   score strictly exceeds the ADR-018 bar at n_symbols and that record's own
   holdout_n_bars / 252; and
3. each present known ADR-049 component count equals its canonical joint sum.

Do not substitute the displayed median-history deflation_bar for individual
survival judgments. Nullable candidate probabilities retain measured incumbent
evidence. Preserve absent legacy joint records, empty/partial component mappings
and unknown-key semantics. No missing attribution is inferred.

This adds no deflation_bar identity, key/completeness policy, null-side
reconciliation, gate threshold, probability rule, estimator, fingerprint,
source, workflow or generated data change. Authoritative sweep reconstruction
inherits the contracts.

## Alternatives

Validating independent root bounds leaves contradictory counts valid. Requiring
new-schema evidence on old artifacts fabricates a compatibility break. Re-judging
survival at a median bar changes the established estimator when histories differ.

## Verification

Observe contradictory valid-typed roots failing tests before code. Cover strict
bar equality/below/above, individual mixed histories, nonpassers, unmeasured
candidate probabilities, partial/unknown mappings, JSON and unchecked nested
reconstruction. Independently review producer agreement and legacy artifact
round-trips, then pass the full foreground delivery gate.

## Reversal

Remove conditional joint-count reconciliation; contradictory modern evidence
becomes acceptable again. Not recommended.

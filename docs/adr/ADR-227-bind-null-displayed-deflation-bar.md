# ADR-227: Bind the null displayed deflation bar to complete searched histories

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 21, ISO 2026-W41
- **Resolves:** FINDING-177
- **Extends:** ADR-018, ADR-036, ADR-037, ADR-213, ADR-224

## Context

A null artifact with complete searched holdout histories accepts an unrelated
finite displayed deflation_bar. Single-shard merge silently normalizes the claim.
Native production and merge define the bar at enclosing N and the median of all
searched holdout years, independently of graduation. All eight committed artifacts
match this definition exactly. Finite individual years can nevertheless overflow
an even-length median to infinity and falsely produce a zero bar; tiny years can
produce an infinite bar. Neither is finite derived evidence.

## Decision

When len(holdout_years) equals n_symbols, require a finite positive median and a
finite expected_max_sharpe_under_null(n_symbols, median_years). Require the stored
deflation_bar to equal that existing result exactly. Refuse contradictory or
nonfinite derived evidence before authoritative merge, without repairing claims.

Preserve empty or incomplete legacy histories as unavailable for this relation;
do not infer measurements or add list-length requirements. Preserve the existing
formula, daily annualization, N=1 zero bar, individual strict survivor judgments
at each graduate's own history, signed maxima and nullable probabilities. Do not
change power fields, thresholds, sources, producers, JSON shape or fingerprints.

## Alternatives and limits

Using graduate histories substitutes a selected subset for searched histories.
A merge-only normalization conceals bad input and leaves standalone reporting
unsafe. Tolerance lacks a measurement-error rationale for an exact producer
projection. Silently accepting overflow changes a measured benchmark into zero;
this ADR refuses it rather than changing the approximation or numerical estimator.

## Verification

Observe direct/JSON/unchecked-merge false bars and nonfinite derived evidence
before code. Protect complete modern/legacy histories, N=1, odd/even and mixed
histories, incomplete/empty legacy lists, and combined-N merge recomputation.
Correct synthetic fixture summaries while preserving original hostile inputs and
rejection assertions. Independently verify native production and all eight
committed artifacts; run affected API consumers and the full foreground gate.

## Reversal

Remove the conditional displayed-bar relationship guard; false reported benchmarks
become acceptable again without changing producer arithmetic.

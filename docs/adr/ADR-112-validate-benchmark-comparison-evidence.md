# ADR-112: Validate benchmark-comparison evidence and baseline

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** Codex autonomous session 8 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-041
- **Supersedes in part:** ADR-013's incomplete overlap handling

## Context

Benchmark statistics use sample variance/covariance and need at least two aligned observations.
The existing implementation checks only for empty alignment. It also measures relative drawdown
without the pre-return unit-wealth baseline, hiding first-period underperformance.

## Decision

`BenchmarkComparator.compare` requires at least two aligned observations, all finite, and every
return greater than -1. Invalid evidence raises `ValueError`. The API comparison remains optional
and converts comparator validation failures to `None`, preserving ADR-013's fail-soft contract.
Relative drawdown is measured from a unit baseline prepended to the compounded relative-equity
path. Valid benchmark formulas and all validation gates remain unchanged.

## Consequences

- Malformed or insufficient overlap cannot become valid-looking benchmark evidence.
- First-period relative losses contribute to benchmark-relative drawdown.
- The public comparator has a precise fail-closed domain; the API continues to fail soft.

## Reversal

Remove the validation and baseline. That would restore malformed scalars and understated relative
drawdown and is not recommended.

# ADR-185: Validate standalone Sharpe return evidence

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-117
- **Extends:** ADR-182, ADR-183

## Context

Standalone sharpe_ratio accepts boolean and complex observations and lets pandas skip missing
rows. Invalid short samples can return the ordinary zero convention. These are malformed return
evidence, not measured constant performance. The moments and interval helpers already validate
complete finite real nonboolean numeric observations through a shared private helper.

Direct consumers calculate numeric engine, benchmark, cross-sectional or regime returns.
Lifecycle callers validate their samples already; engine and benchmark builders provide complete
returns. No intended missing, boolean or complex caller contract was found. Regime analysis on
malformed external returns will now fail rather than score a skipped subset.

## Options Considered

1. Reuse the shared source validator before all standalone Sharpe shortcuts.
2. Drop or fill malformed observations. Invents evidence and can hide invalid caller inputs.
3. Validate only selected callers. Leaves the public statistical primitive inconsistent.

## Decision

Call _validate_complete_return_sample before the length shortcut in sharpe_ratio. Reject missing,
nonfinite, boolean, complex and nonnumeric source Series with ValueError. Preserve the existing
annualized sample-standard-deviation estimator and zero convention for valid numeric empty,
singleton, constant or native nonfinite-standard-deviation samples. Accept complete nullable
numeric dtypes and finite signed observations, including returns at or below minus one: this is
a statistical primitive, not a compounding-domain check. Do not repair source data or change gates.

## Consequences and limits

Invalid inputs fail consistently even before short-history and constant shortcuts. Finite valid
callers keep their native arithmetic and results. Missing-row padding cannot silently produce a
score. Tests first reproduce invalid singleton, padded, boolean, complex and infinite evidence,
then protect valid nullable, signed and degenerate samples. Full application gates check consumers.
This does not redesign extreme-scale floating-point moments or guarantee every finite sample
produces a finite Sharpe; those remain separate numerical questions.

## Reversal

Remove the standalone validation call. This reopens FINDING-117.

# ADR-183: Bind Sharpe intervals to complete observations

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-116
- **Extends:** ADR-109, ADR-111, ADR-182

## Context

The interval computes Sharpe from pandas moments that skip NaNs, but its history minimum and
standard error count every supplied row. Missing padding can manufacture eligibility or precision.

## Options Considered

1. Require complete finite real numeric source observations before length shortcuts and inference.
2. Drop missing rows and use their remaining count. This changes the supplied research sample.
3. Validate the standalone Sharpe helper globally. This changes more callers than the count defect
   requires; that separate public surface is recorded in FINDING-117.

## Decision

After the existing confidence-domain validation and before sample-length shortcuts, apply the same
complete finite real nonboolean numeric validation as return_moments. Extract that existing check
into one private helper without changing return_moments behavior. Preserve valid short None,
complete nullable numeric, signed samples, genuine constant-series intervals, one-year minimum,
years=len/252, standard-error formula, quantile arithmetic and iid_normal metadata.

## Consequences and limits

Missing rows cannot add nominal history or narrow a reported band. No filling, dropping or coercion
is performed. The guard does not establish daily cadence or dependence-robust coverage; it binds
sample count to complete observations only. Standalone Sharpe invalid evidence and near-one
confidence quantile overflow are separately recorded in FINDING-117/118 and remain outside this
correction. No validation threshold, generated data, calibration identity or workflow changes.

## Reversal

Remove interval source validation. This reopens FINDING-116.

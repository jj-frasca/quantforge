# ADR-186: Validate compounded return source evidence

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-119
- **Extends:** ADR-110, ADR-182, ADR-185

## Context

The log-compounding helper converts return observations to float64 before checking finite values
and positive wealth. This accepts boolean/string observations and discards complex components.
Public total_return and annualized_return also return zero for empty malformed dtypes before any
validation. Checked production consumers only pass engine net returns via BacktestMetrics.

## Options Considered

1. Validate source evidence in each public compounding primitive before its empty shortcut.
2. Validate inside the shared private log helper only. Leaves empty public inputs unchecked and
   changes the private drawdown path's contract unnecessarily.
3. Preserve conversion as implicit parsing. Loses source evidence, including imaginary values.

## Decision

Apply _validate_complete_return_sample at entry to total_return and annualized_return, before
empty shortcuts. Require complete finite real nonboolean numeric source observations. Preserve
numeric empty zero, complete nullable numeric support, the strict returns >-1 positive-wealth
contract, and all native log-compounding/annualization and finite-positive output checks.
Leave the shared private log/drawdown helper unchanged; public entry guards make source validity
explicit without widening private scope. No filling, dropping, parsing or data modification.

## Consequences and limits

Invalid source dtypes fail before lossy conversion, including empty malformed histories. Tests
reproduce source coercion before the fix and protect signed >-1 samples with an independent
product-of-wealth oracle, complete nullable compatibility, empty numeric zero and original wealth
refusal. This does not change compounding identities, graduation thresholds or calibration identity.
Sortino source/target and Calmar scalar validity are separately documented findings 120 and 121.
Extreme finite arithmetic and private direct-call contracts remain separate limitations.

## Reversal

Remove the two public source-validation calls. This reopens FINDING-119.

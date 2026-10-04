# ADR-168: Validate forward lifecycle input boundaries

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 28 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-099
- **Extends:** ADR-020, ADR-025, ADR-073, and ADR-166

## Context

Lifecycle helpers can report a grace/no-trade hold before inspecting their paired returns or policy.
Nonfinite thresholds can also disable comparisons, while nonpositive rolling windows change the
sample silently. Policy instances and unchecked copies are not revalidated at the decision boundary.

## Options Considered

1. **Validate policy and paired inputs before every early return.**
   - Pro: malformed evidence/configuration produces an error instead of a lifecycle verdict.
   - Con: callers with invalid injected inputs now fail rather than receive a hold.
2. **Validate only after the grace period.**
   - Pro: avoids checking unused statistics.
   - Con: a hold would still assert a valid policy/evidence identity that was never checked.
3. **Clamp policy values or drop bad observations.**
   - Pro: maximizes verdict availability.
   - Con: silently changes the policy or forward sample and is methodologically dishonest.

## Decision

Always revalidate both exit-policy models. Require nonnegative grace periods and finite nonnegative
drawdown limits, positive rolling windows, finite Sharpe floors, and a positive single-name no-trade
horizon. Preserve every default, finite negative Sharpe floors, zero grace, and finite drawdown
limits above one used to deliberately disable that trigger in isolated diagnostics.

Both pure lifecycle functions validate exactly aligned, unique ascending return indexes and real
nonboolean/noncomplex numeric finite returns greater than -1 on each side before grace/no-trade
holds. Preserve aligned empty series and generic/naive indexes. Single-name trade counts must be
nonboolean integers between zero and observed bars. Both frame/panel evaluate wrappers also
revalidate policy before their no-forward-data returns. Do not repair, fill, align, or clip inputs.

## Consequences

- Invalid policies and missing/misaligned/undefined evidence cannot produce a hold or exit verdict.
- Normal valid-input decisions, lifecycle defaults, predicates, and thresholds remain unchanged.
- Unchecked model copies fail at the decision boundary; model_copy itself remains unchecked.
- These guards validate inputs, not arbitrary extreme floating-point arithmetic. Finite individual
  returns alone do not guarantee compounded wealth or variance calculations avoid overflow.
- Managed providers retain their existing fail-soft behavior on validation exceptions. No generated
  data, score schema, acquisition behavior, or broker execution changes.

## Reversal

Remove policy/paired-input guards. That reopens FINDING-099 and is not recommended.

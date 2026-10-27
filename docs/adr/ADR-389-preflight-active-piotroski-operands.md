# ADR-389: Preflight active Piotroski input operands

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session8, ISO2026-W44
- **Resolves:** FINDING-330 within active piotroski_f_score input consumption
- **Extends:** ADR-029/117/155/384/385

## Context

Present nonfinite operating cash flow can award two favorable boolean points and
become a finite accepted pool score. NaN can instead erase to an ordinary false
signal. Canonical synthetic parser and independent object witnesses confirm the
gap; no production/vendor incidence is established. Existing safety/record numeric
boundaries cannot recover invalidity after the F-score booleans form.
Independent data/research reviews approve a local active-operand boundary rather
than global history or ratio changes. A pre-source baseline freezes291 histories
and873 complete producer JSON/Python claims plus the whole quality module AST.

## Options considered

1. **Preflight present active operands locally (chosen).** Stops erased invalidity
   without changing Annual/history construction, shared division or unrelated consumers.
2. **Guard only CFO or only nonmissing ratio pairs.** Rejected: leaves the same
   defect in other active signals and lets missing peers hide invalid evidence.
3. **Make all Annual inputs finite globally.** Deferred: broadens provider and
   valuation availability and refuses ignored rows/fields outside this consumer.
4. **Convert invalid values to None/False or repair arithmetic.** Rejected: invents
   availability or a score; no recovery or changed mathematical estimator is justified.

## Decision

Preserve the existing fewer-than-two-years all-zero return. After selecting t,p
and calculating p_adjacent, preflight these latest fields in this order:
net_income,total_assets,operating_cash_flow,long_term_debt,total_current_assets,
total_current_liabilities,gross_profit,revenue.

Only when p_adjacent, append latest.shares_diluted followed by prior.net_income,
total_assets,long_term_debt,total_current_assets,total_current_liabilities,
gross_profit,revenue,shares_diluted, in that order. Every present value must be
finite; None remains allowed but cannot hide another invalid selected operand.
Raise plain ValueError naming latest/prior.field and Piotroski F-score on the first
invalid value before any ratio/boolean/missing-peer/zero-denominator shortcut.

Keep all existing native arithmetic/comparisons, fiscal selection/adjacency,
missing-input false signals, score thresholds, F324 same-year ROA and global
schemas unchanged. Prior OCF, older rows, gap-disabled prior fields/latest shares,
and unrelated fields remain outside the guard. The latest eight ratio inputs are
currently read even when trend comparison is disabled; retain that execution scope.
No new output/model guard, import, shared-ratio change or numerical recovery.

## Consequences, verification and reversal

Availability is deliberately stricter for invalid active operands even when peers
are missing/zero or another signal fails. quality_score calls F-score first, so
its refusal now precedes safety/GP evaluation when both are invalid. Consumer
errors remain outside sweep acquisition recovery and can fail a shard before
output; no skip/fallback/partial-output policy is added. Distress-only consumers
still use their existing separate safety guard.

Finite-source ratio overflow, exact-real comparison precision, economic denominator
ranges, F324 paper-formula differences, source period/PIT truth and historical
lost inputs remain separate. No search/gate/cost/ranking threshold, config hash,
accounting-v14, provider or generated-data change.

Actual pre-code RED must cover all active fields, direct/quality/record consumers,
canonical parser witnesses, missing-peer/zero cases and error precedence. Preserve
short histories, inactive rows/fields, None/finite/coercion and finite-overflow
controls with Hypothesis invariants. Replay873 complete producer claims and whole
AST outside the exact preflight; obtain independent final reviews and foreground
full gates before individual safe publication and exact CI verification.

Remove only this preflight block to reverse; preserve the finding, which reopens.

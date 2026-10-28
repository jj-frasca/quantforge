# ADR-397: Refuse inconsistent Piotroski ratio predicates

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Codex autonomous session12, ISO2026-W44
- **Partially addresses:** FINDING-331
- **Extends:** ADR-029/117/155/389/390/395

## Context

F331 ordinary rounding and nonzero subnormal collisions remain after ADR-395.
Independent research constructs24 histories spanning all six pair components,
both regimes and denominator signs through actual score/quality/record producers.
Exact accepted-operand predicates are True where native strict booleans areFalse.
This establishes constructed correctness loss, not market prevalence or source
truth. Both prospective research and data reviews approve local refusal.

## Options Considered

1. **Six exact predicate checks (chosen).** Preserve native scores when supported
   exact accepted-operand comparisons agree; refuse disagreement or unavailable
   precision. Broader than accrual-only, but local and uniformly testable.
2. **Accrual-only shared-denominator identity.** Smaller for canonical floats;
   leaves five demonstrated trends unresolved and needs explicit unchecked-type
   scope. Mixed NumPy integer/float comparison can itself erase ordering.
3. **Exact score replacement.** Recovers some points but changes producer scores
   and still cannot certify paper/source truth. Not adopted.

## Decision

Finish all current raw guards, eleven native assignments, complete finite-result
loop and complete zero-underflow loop unchanged. Then visit delta_roa_positive,
accruals_quality, delta_leverage_negative, delta_current_ratio_positive,
delta_gross_margin_positive, delta_asset_turnover_positive in signal order.
Only check a pair when both native ratios exist. Reconstruct each quotient using
exact rational forms of its accepted numerator and denominator. Normalize Integral
scalars directly viaint; otherwise use native as_integer_ratio without float
projection. Require a two-element tuple with nonboolean Integral members and
nonzero denominator, normalize both Pythonints, then construct Fraction.
The standard exact protocol is trusted to represent its scalar faithfully;
structural checks cannot certify arbitrary custom method truthfulness. Existing
native arithmetic/finite checks still bound unchecked mixed-type support.

Compare the SAME strict predicate, including '<' for leverage. If native and exact
predicates disagree, raise plain ValueError naming the component with
`<component> must preserve exact operand ordering for Piotroski F-score`.
An unavailable/malformed exact protocol raises
`<component> requires exact operand ratios for Piotroski F-score`.
This is an explicit additional compatibility/availability restriction for active
unchecked scalars. Do not manufacture missingness or substitute exact scores.
None/zero-denominator, short history and gap-disabled prior behavior persist;
latest accrual still checks across gaps. Negative denominators remain permitted.

## Consequences and verification

Raw/nonfinite/zero error precedence remains unchanged before any new pair check;
first new refusal follows signal order and can precede later safety errors.
Quality/record/sweep propagate refusal without recovery, skip or partial output.
No shared _ratio, schema, raw signal, source/provider, threshold, fingerprint,
v14, generated record, calibration or frozen cohort change. Exactness concerns
stored accepted scalars, not earlier decimal facts, accounting periods or PIT.
F324/F322 and arbitrary custom numeric semantics remain outside this correction.

TDD six components through all three consumers, both collision regimes/signs,
false-direction preservation, equality, missing/gap/zero/short controls, exact
standard scalar adapters and malformed protocol refusals, named precedence,
properties and fully mocked real sweep. Replay288 histories/864 complete claims
and whole AST outside the exact declared additions. Independent research/data
reviews, full foreground make check-all, individual safe push and exact master
CI verification are required. Reversal removes these local checks/helper/imports;
retain finding and ADR, and never rewrite accepted historical records.

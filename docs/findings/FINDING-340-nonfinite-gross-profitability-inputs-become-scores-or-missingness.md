# FINDING-340: Nonfinite gross-profitability operands become scores or missingness

- **Date:** 2026-10-29, Codex autonomous session20 (ISO2026-W44)
- **Status:** Corrected within latest-year raw GP input consumption under ADR-405
- **Severity:** Medium for direct/in-process invalid financial evidence
- **Producing revision:** `434e14e2`
- **Affected:** `gross_profitability`, single-year `quality_score`, record missing-leg consumption

## Evidence

An ordinary one-year synthetic history with assets100 and gross profit NaN or
positive infinity returns that nonfinite gross-profitability ratio. The composite
clips it to a full GP leg and reports finite quality0.5, while retaining the raw
nonfinite component. Negative infinity returns finite quality0 with the raw
negative-infinite component. FundamentalRecord already refuses all three through
its existing numeric boundary: these cases do not establish a durable favorable
quality score or screening effect.

With gross profit NaN and assetsNone, or gross profit positive infinity and
assets0, the direct scorer instead returns None. The composite and record accept
quality0 and GPNone. This establishes invalid raw evidence erased into an accepted
missing leg, without demonstrating a favorable point or admission change.
Infinite assets can also yield a finite standalone ratio0; composite safety already
refuses those assets. Parent and independent research reproduce 13 synthetic controls.
No actual SEC response, vendor incidence, company, graduate, trade, calibration or
production admission effect is established; no provider or real search was run.

ADR-380/F321 protects parser-derived gross-profit subtraction, not every direct
GP operand. ADR-389/F330 protects active Piotroski operands and deliberately keeps
its fewer-than-two-row zero result. At the producing revision, the direct GP scorer had no raw-input guard.

## Bounded correction and limits

Preserve empty-history None. After selecting the latest year, require present
gross_profit followed by total_assets finite before _ratio or its None/zero
shortcuts. First invalid input raises plain field-named ValueError identifying
gross profitability. None itself remains valid but cannot hide invalid peers.
Keep all finite native division, zero/negative domains, older rows and global
schemas; add no catch/fallback, substitution or numerical recovery.

The composite calls Piotroski, GP, then safety. On one-year histories new GP input
errors intentionally precede safety source/finite-derived errors. Existing two-year
Piotroski refusal still occurs first. Direct GP continues to ignore unrelated
safety fields. Record errors propagate; no skip/partial-output policy is added.

Finite operands can still produce infinite GP ratios; those intermediate outputs
and existing record refusals remain unchanged by this raw-input-only correction.
Finite underflow, signed zero, ordinary rounding, economic denominator restrictions,
Novy-Marx period definitions, source/PIT truth and historical lost evidence remain
separate. No threshold, search/gate identity, accounting-v14, generated record or
frozen-cohort change is authorized.

## Verification

Before implementation, 1,731 complete finite/None direct/composite/record outcomes,
whole quality-module AST and three original test SHAs were frozen. Parent and
independent research replay the pre-source baseline exactly. It includes empty,
adjacent/gapped histories, ignored older invalid rows, signed/negative/zero/small/
large operands, finite overflow/underflow and existing downstream refusal outcomes.
The actual pre-code run has 79 failures and 24 controls passing in 1.23s:
43 missing refusals and 36 expected named-error mismatches, without harness errors
or a production diff. All 103 new cases pass after the sole six-line guard;
the parent focused suite passes 533 synthetic tests. Independent research review
approves all six paths, passes 558 synthetic tests and independently replays all
1,731 outcomes, the whole scoped AST and original test SHAs exactly.
The session ledger tracks foreground full-gate and exact publication CI
verification and their completion receipts. No generated record or frozen evidence is rewritten.

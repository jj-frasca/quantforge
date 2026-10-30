# ADR-407: Preflight the consumed DCF share operand

- **Status:** Accepted
- **Date:** 2026-10-30
- **Deciders:** Codex autonomous session21, ISO2026-W44
- **Resolves:** FINDING-342 within reached latest-share consumption
- **Extends:** ADR-022/373/401/406

## Context

Nonfinite diluted shares can become a finite zero DCF or ordinary missingness.
An inactive P/S branch allows that evidence through composite validation. Parent
source review and independent synthetic research confirm the witness; production
incidence and any admission effect are unmeasured.

## Options considered

1. **Check the reached DCF share operand (chosen).** Narrowly rejects invalid
   evidence before comparison/division; adds a refusal for previously accepted
   malformed inputs and may reduce availability.
2. **Check final composite output only.** Already present, but cannot recognize
   zero formed by division by infinity or an erased negative-infinite denominator.
3. **Validate all history globally.** Covers more consumers but changes inactive
   fields and earlier missing-base paths without a demonstrated need here.
4. **Convert invalid shares to None.** Preserves availability but conceals invalid
   evidence as missingness and changes the meaning of the result.

## Decision

Immediately after assigning latest.shares_diluted, following the existing missing
and nonpositive base returns, require every present share operand finite with
math.isfinite. Raise plain ValueError naming shares_diluted, fiscal year and DCF.
Then retain the existing missing/nonpositive shares return and all subsequent
native arithmetic. None remains missing; finite nonpositive shares stay flagged.
Do not inspect historical shares, inactive net income or other fields. Retain
base/proxy selection, flags, growth/chronology rules, assumptions, schemas and
consumer exception boundaries. Do not recover or substitute missing evidence.

## Consequences, verification and reversal

Every reached nonfinite latest share refuses, including when growth would later
fail. Earlier base returns still precede share consumption. Ordinary finite
results remain exact on the bounded frozen baseline; this is not a universal
numerical equivalence proof. Provider scoring remains outside acquisition fallback: a hunt records the refusal
as a per-symbol error before search; a sweep scorer can fail its shard before
output. No new catch or partial-success policy is introduced.
No estimator expression, threshold, fingerprint,
v14, generated data, cohort or historical reconstruction changes.

Observe pre-code RED for direct DCF, composite and fundamental-record witnesses,
all three nonfinite kinds, named error and precedence. Retain missing/nonpositive
and dormant-field controls; use Hypothesis against a flat-growth perpetuity.
Replay 150 full ordinary outcomes, obtain independent final research review, run
foreground make check-all and verify exact CI after safe individual publication.
Removing only this local guard reverses the decision and reopens the finding.

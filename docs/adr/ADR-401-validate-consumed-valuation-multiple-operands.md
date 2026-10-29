# ADR-401: Validate consumed valuation multiple operands

- **Status:** Accepted
- **Date:** 2026-10-29
- **Deciders:** Codex autonomous session16, ISO2026-W44
- **Addresses:** FINDING-337
- **Extends:** ADR-022/023/373/398

## Context and Options

Ordinary validated infinite EPS becomes finite P/E0/rank0 and a maximum cheapness
component. Computed/final finite guards cannot recover erased operand validity.
Independent data/research reviews confirm the witness and narrow policy.

1. **Consumption-scoped wrappers (chosen).** Preserve native expressions and
   dormant branches; add local named refusals. More checks are needed than a
   single entry preflight, and malformed consumed evidence reduces availability.
2. **Whole-history/schema preflight.** Simpler complete validity, but rejects
   demonstrably unused fields and changes unrelated consumers/error precedence.
3. **Only check arithmetic operands.** Smaller, but NaN/-inf comparisons can
   silently change historical eligibility before arithmetic is reached.
4. **Recover/filter invalid observations.** Preserves some output availability
   but changes the ranking population and fabricates unsupported evidence.

## Decision

Add _finite_operand(value, label) to multiples.py. Require math.isfinite(value),
raise plain ValueError `{label} operand must be finite for valuation multiples`
otherwise, and return the ORIGINAL value without float projection or coercion.
Wrap exactly the existing first numeric uses inside compute_multiples:

- Current P/E: EPS in <=0; current price in the quotient only for positive EPS.
- Historical P/E: price in >0, then present EPS in >0.
- Current P/S: revenue in <=0 after the shares-None branch; current price then
  shares in the multiplication only for positive revenue.
- Historical P/S: present price, present shares and revenue in their >0 tests,
  retaining original left-to-right short circuits and traversal.

Use labels current/historical P/E price/EPS and current/historical P/S
price/shares/revenue. Labels identify consumed fields, not original row ordinals.
Retain P/E calculation/history/_ranked before all P/S work and existing computed
guards. Never inspect dormant fields, change None/finite eligibility, normalize
operands, replace expressions, add positivity rules or modify shared schemas.
Finite booleans/native scalar arithmetic retain previous behavior; this adopts
no general original-type or unchecked protocol contract.

## Consequences and Verification

Nonfinite consumed eligibility/arithmetic operands refuse earlier, including
malformed values formerly excluded by comparison. Dormant values remain outside
this guard. All finite arithmetic, flags, counts, strict ranks and thresholds
stay. Existing provider scoring errors propagate outside acquisition recovery;
hunt handling stays per symbol and record quality still precedes valuation.
New refusal order is explicit, without promising old malformed-input errors.
No full source/PIT/period truth, precision recovery, production incidence,
historical repair, generated data, fingerprint, v14 or cohort change is claimed.

Before source edits freeze complete ordinary/missing/negative/zero/tie producer
claims, schema and AST. Observe failing tests before implementation, including
ordinary validation, each operand, dormant branches, co-invalid precedence and
real injected provider/hunt propagation. Use a native finite Hypothesis rank
oracle; retain computed-overflow tests. Stripping exactly the helper/wrappers
must recover the old whole-module AST. Require independent final reviews,
foreground make check-all, individual safe publication and exact master CI.

Reversal removes the helper/wrappers and reopens F337; preserve written evidence
and historical records. Never rewrite generated data.

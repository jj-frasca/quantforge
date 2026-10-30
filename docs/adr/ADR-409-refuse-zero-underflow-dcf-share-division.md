# ADR-409: Refuse nonzero DCF equity divided to zero per share

- **Status:** Accepted
- **Date:** 2026-10-30
- **Deciders:** Codex autonomous session22, ISO2026-W44
- **Partially addresses:** FINDING-344; earlier arithmetic precision remains open
- **Extends:** ADR-022/373/395/407/408

## Context and options

Finite native equity can divide to zero and erase the DCF component as ordinary
missing margin of safety, while a composite1 and default passing screen remain.
Independent research/data confirm this actual synthetic producer path and its
exact accepted-float nonzero quotient. No actual vendor/run effect is established.

1. **Local final-division zero-loss refusal (chosen).** Identifies certain loss of
   nonzero native evidence and preserves ordinary arithmetic; reduces availability
   without recovering extreme values or covering earlier arithmetic loss.
2. **Exact arithmetic or rescaled DCF recovery.** Could widen the measurable domain,
   but changes financial arithmetic and requires a separate precision policy.
3. **None, zero or a missingness flag as fallback.** Keeps availability, but preserves
   the demonstrated component erasure and can retain favorable composite admission.
4. **Require every zero intrinsic value invalid.** Simpler, but rejects genuine
   zero equity admitted by current settings and changes an unrelated economic policy.

## Decision

After the unchanged native projection/terminal/discount accumulation, assign
value_per_share = equity_value / shares once. Before constructing the existing
result, if equity_value !=0.0 and value_per_share ==0.0, raise plain ValueError:
`intrinsic_value_per_share must not underflow to zero for DCF`.
Return the computed value in the same existing field otherwise. Do not add a
second division, shared helper, model/schema policy, rounding tolerance or recovery.

Both signed quotient zeros refuse for nonzero numerators. Genuine signed-zero
numerators, every nonzero native quotient including subnormals, missing/nonpositive
base/share early returns, prior raw guards, growth selection and chronology,
assumptions, flags and earlier native arithmetic/errors stay. Earlier zero
accumulators remain outside this guard. Existing nonfinite output behavior stays;
this is neither a universal measurability proof nor a financial threshold change.

## Consequences, verification and reversal

Scoring errors propagate through existing composite/record/provider paths; the
universe records explicit per-symbol failure before downstream frame acquisition
and search, while a sweep scorer can fail before shard output. Preserve acquisition
recovery and introduce no partial output or unscored substitution. No historical
record reconstruction, generated edit, gate/search fingerprint, v14, calibration
or frozen cohort change follows.

Write failing direct/composite/record/provider/universe and financial Hypothesis
tests before source changes. Cover proxy/FCF, both signs, singleton/multirow,
true zero and nonzero subnormal controls. Independently prove nonzero quotients
in the refusal domain, replay 1,140 complete ordinary outcomes and the whole AST
outside this exact final assignment/guard/field substitution, and preserve six
original test hashes. Require final research/data review, foreground make check-all,
individual safe sync/push and exact master CI.

Removing only the final assignment/guard and restoring the original quotient
expression reverses this refusal and reopens F344. Retain the finding and ADR.

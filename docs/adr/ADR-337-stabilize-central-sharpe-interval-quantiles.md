# ADR-337: Stabilize central Sharpe interval quantiles

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 10, ISO 2026-W43
- **Resolves:** FINDING-285
- **Extends:** ADR-109/111/183/184

## Context

ADR-184 evaluates the positive Gaussian quantile with norm.isf((1-confidence)/2)
to preserve near-one tails. It explicitly defers very small confidence. For
confidence 1e-20, subtracting from one rounds away the accepted confidence and
returns a zero quantile. A complete symmetric 252-return sample then reports
[0,0], although the correct nonzero bounds are representable. At 1e-16 the
issued quantile's forward Gaussian central mass differs by about 11% relative.

This concretizes a known deferred numerical limitation, not a regression in
the near-one repair. Forward Gaussian mass tests the quantile within the
existing iid-normal asymptotic model; it is not empirical repeated-sample or
market coverage. No actual production occurrence or default-95% defect is
established.

## Options considered

1. Use central inverse-erf evaluation at confidence<=0.5, retaining the existing
   inverse-survival expression above 0.5. Avoids cancellation and preserves
   default/high-tail arithmetic, with explicit representational limits.
2. Use inverse-erf everywhere. Mathematically equivalent, but needlessly
   reevaluates the already repaired high-tail/default path.
3. Cap or floor confidence. Removes valid requests to hide a numerical defect;
   rejected.
4. Keep the current documented limitation. Honest but unnecessarily returns
   collapsed intervals whose correct endpoints are representable.

## Decision

For confidence<=0.5 evaluate the same positive Gaussian quantile as
sqrt(2)*scipy.special.erfinv(confidence). Otherwise retain the exact existing
float(norm.isf((1-confidence)/2)) expression. Central Gaussian mass is
erf(z/sqrt(2)), so both branches invert the same mathematical probability.
The 0.5 switch chooses a numerical representation, not a statistical acceptance
threshold. Installed primary erfinv documentation identifies a real inverse
on (-1,1); the central branch stays away from its infinite endpoints.
Multiply Python-float sqrt(2) and inverse-erf results. This preserves the
binary64 product while avoiding a new NumPy scalar-multiply underflow warning
or FloatingPointError for subnormal confidences under caller warn/raise policy.
Add no error-state context or warning filter.

Preserve confidence-domain validation, complete-return validation, sample/history
minimum, Sharpe, Lo standard error, bound arithmetic, confidence value,
iid_normal identity and all API/UI shape. Add no coercion policy, confidence
floor/cap, estimator or dependence-robust inference.

## Consequences and limits

Representable zero-centered tiny-confidence intervals recover; central finite
results can change by ordinary rounding, including one ULP at confidence 0.5.
All existing >0.5 arithmetic, including default 95% and nearest-one confidence,
remains exact. The source score and standard-error calculation do not change.

No universal correct rounding or uniform relative-accuracy claim follows.
At confidence 2**-1072, subnormal intermediate/product rounding can leave one
confidence ULP of forward-mass error, roughly 25% relative. Test normal central
probabilities with a relative forward oracle and zero absolute tolerance;
treat selected subnormals separately with explicit quantization bounds.
Nonzero centers can still absorb a halfwidth below endpoint spacing. This
repairs quantile cancellation, not endpoint resolution, arbitrary wider/custom
scalar arithmetic or frequentist coverage under dependence/non-normality.

No financial threshold, model, selector, fingerprint, accounting-v14, generated
record or frozen cohort change. No production rate claim or historical relabel.

## Verification and reversal

Record real complete-source RED before runtime edits. Test representable tiny
central mass, branch neighbors, signed bounds, ordinary/default/high-tail
controls, source/confidence precedence and a financial-math forward-inverse
Hypothesis property. Preserve 56 frozen >0.5 full-result/short-None payloads
and every prior runtime statement except the import, quantile expression and
docstring. Independently review and run foreground make check-all before
individual push and exact CI. Restore the old quantile expression to reverse,
reopening FINDING-285 without changing historical evidence.

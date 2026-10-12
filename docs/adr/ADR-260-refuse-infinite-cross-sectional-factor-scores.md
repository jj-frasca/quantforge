# ADR-260: Refuse infinite cross-sectional factor scores

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 2, ISO 2026-W42
- **Resolves:** FINDING-209
- **Extends:** ADR-024, ADR-257

## Context

A shipped momentum configuration can overflow cumulative price ratios while all
prices and adjacent asset returns remain finite. Infinite factor scores enter
rank(method="first") as ordinary observations. Distinct unrepresentable ratios
become false ties, supplied column order may reverse the true momentum ordering,
and the portfolio kernel publishes finite returns from the wrong legs.

## Options Considered

1. Refuse infinite scores at the shared ranker before ranking.
   - Pro: catches every caller without changing valid ranking or NaN warmup.
   - Con: declines overflowed factor evidence rather than recovering the ratio.
2. Recover each strategy's ratios with logarithms/scaling.
   - Pro: could preserve more mathematically defined orderings.
   - Con: changes factor arithmetic and needs separate estimator evidence.
3. Treat infinity as a ranked extreme or discard it as NaN.
   - Pro: keeps computing.
   - Con: invents ties or changes the ranked universe without evidence.

## Decision

After the existing quantile check and before ranking, long_short_weights refuses
any exact positive or negative infinity in the supplied signal panel. Use native
DataFrame infinity membership without float conversion. Keep original frames,
NaN/pd.NA exclusion, finite wide/nullable/object numeric scores, bool compatibility,
empty panels, supplied tie order and every rank/weight/return formula unchanged.
No new dtype ban is bundled with this correction. Existing unsupported payloads
remain unsupported. No clipping, filling, dropping, scalar fallback, NumPy error
state change, estimator, threshold, identity or generated record change.

This guard does not certify finite-score arithmetic precision or detect a generator
that has already replaced overflow with missing values. No historical production
or calibration contamination is inferred from the synthetic reproduction.

## Verification and reversal

Observe RED for signed infinities, degenerate/nullable/wide/Decimal panels and the
shipped momentum grid fixture before production edits. Preserve finite native
scores beyond float64 range, missingness, empty output, quantile precedence and
all standard generators. Include an adversarial Hypothesis score-domain invariant,
independent review and foreground make check-all before commit/push/exact CI.
Remove the infinity guard to reverse this correction and reopen FINDING-209.

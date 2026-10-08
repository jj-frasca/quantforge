# FINDING-151: Foundation Sharpe accepts partial underflow and lost zero means

- **Date:** 2026-10-07
- **Severity:** High — inaccurate foundation evidence feeds observed/holdout selection
- **Status:** Resolved by ADR-209

## Evidence

At revision f1891104, `sharpe_ratio([-1e-161, 2e-161, -3e-161, 4e-161])`
returns `2.5506443722026937`; an independent 800-digit Decimal sample-standard-
deviation oracle constructed from the exact floats gives `2.5528888301902897`.
Native variance is finite and positive, but partial square underflow has already
lost precision. Finite-result checks do not detect this failure.

`[-1e100, 1e-200, 1e100]` returns zero while the same oracle gives
`5.291502622129181e-300`. Native mean reduction loses the middle observation;
math.fsum of the original floats is nonzero. Likewise,
`[-1e-160, 1e-160, nextafter(0, 1)]` returns zero instead of the representable
`2.6143496604729036e-163`. These are independent offline reproductions, not a
claim that a committed graduate changes.

Independent final review additionally found that recovering the stable sum and
then dividing by sample count first loses `[-1, smallest_subnormal, 1]`'s
representable `2.5e-323`. With 97 zero observations added, the exact rounded score
is still nonzero. Recovery must annualize and divide by normalized dispersion
before dividing by sample count; mean-only scaling is insufficient at this edge.

ADR-203 recovered nonfinite/zero dispersion, but accepted all finite positive
native dispersion and all finite zero means. Unlike descriptive Sortino, this
helper feeds foundation Sharpe, its iid interval, and search/gate consumers.
The correction must invalidate prior calibration identity; thresholds and
generated records cannot be changed to conceal missing current evidence.

## Proposed boundary

Detect native underflow locally, require original stable-sum evidence before
accepting a zero mean, and use stable normalized sums in the existing cancelling-
scale recovery. Preserve nonzero native scores without detected arithmetic
failure. Arbitrary nonzero cancellation precision remains outside this slice;
ratios genuinely below float64 range may still round to zero.

## Resolution and limits

ADR-209 detects native mean/std/score underflow and requires original stable sum
evidence before accepting native zero mean. Float64 normalized sample std and
stable normalized sum recover the same Sharpe, with annualization/std division
before sample-count division. Thirty-six initial RED cases (including two
identity checks) and twelve additional subnormal-order RED cases precede their
respective corrections. Nine preservation cases keep ordinary native scores and
genuine zero conventions. Independent review approves the arithmetic and scopes.

Accounting v10 prevents historical v9 calibration from matching the corrected
procedure. No graduate impact, current distribution, generalized precision,
dependence-robust interval, threshold change or generated-record rewrite is
inferred from these numerical regressions. F152 separately records the remaining
descriptive Sortino recovery-order question.

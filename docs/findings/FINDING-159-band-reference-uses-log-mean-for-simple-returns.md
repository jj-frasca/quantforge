# FINDING-159: Band reference uses log mean for simple returns

- **Date:** 2026-10-08
- **Severity:** High — reference optimality and power interpretation
- **Status:** Open
- **Reviewed implementation:** `bb3ef2e0`; unchanged at `1c319fdf`

## Reproduction and derivation

ADR-042's generator constructs `close = 100 * exp(level + deviation)`.
Conditional on the previous latent deviation `d`, its next log return is
Gaussian with mean `m = drift + (rho - 1) * d` and variance
`v = level_vol**2 + deviation_vol**2 * (1 - rho**2)`.
The generator's `conditional_mean` stores `m`. `oracle_sharpe_of` takes its
sign, but scores `close.pct_change()`, which is a simple return.

The exact conditional mean of that simple return is `expm1(m + v / 2)`.
Its sign differs from the stored reference for `-v / 2 < m < 0`.
With half-life 1, deviation share 0.5, total volatility 0.012, drift
0.0003 and previous deviation 0.00065, `rho = 0.5`, `v = 0.000126`,
`m = -0.000025`, and the conditional simple mean is approximately
`+0.000038000722`. The historical reference shorts a positive conditional
simple-return mean.

An independent NumPy reconstruction used 4,096 bars with those generator
parameters and seeds 2026100800, 2026100801 and 2026100802. It reproduced
the production conditional log-mean series exactly and found respectively
38, 17 and 19 opposing signs among each seed's 4,095 usable predictions.
These are source-only sign checks, not search trials or power estimates.
Root and independent research review both reproduced the issue.

## Consequences and scope

Historical gross/net band scores remain scores of the implemented reference
strategy. They do not establish a conditional simple-mean benchmark, a
cost-aware optimum, a sample maximum, or an upper bound on causal strategies.
ADR-061's observable reference uses the same log-mean sign convention.
If its Gaussian filtered posterior is correct, the predictive log variance
also includes `(rho - 1)**2 * posterior_deviation_variance`; substituting
only the latent innovation variance would not correct that reference.
This finding does not certify the filter's initialization or posterior.

Claims that near-zero observable net reference scores prove no recoverable
edge, or that every graduation would necessarily be wrong, need qualification.
No change to search outcomes, detector counts, or historical measured scores
is asserted. This is distinct from FINDING-155's AR drift-intercept omission.

A future governed correction needs test-first simple-return conditional-mean
and predictive-variance contracts, review of filter initialization, explicit
methodology attribution and its own ADR. This report changes no generator,
reference implementation, threshold, calibration identity or data artifact.

## Verification

The analytic Gaussian expectation, numerical counterexample, independent
source reconstruction and research review above precede this documentation
change. Independent final research review approved the report and cold-memory
qualification. Full foreground `make check-all PYTEST_WORKERS=4` passed
3,237 backend tests (97.54% coverage) and 359 frontend tests (97.63% statements).

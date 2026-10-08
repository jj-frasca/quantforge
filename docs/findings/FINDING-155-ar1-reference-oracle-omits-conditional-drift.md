# FINDING-155: AR(1) reference oracle omits conditional drift

- **Date:** 2026-10-07
- **Severity:** Medium — effect-size/capture interpretation misidentifies its benchmark
- **Status:** Open; no production correction or historical relabeling

## Evidence

The unchanged generator has `X_t = phi * X_(t-1) + shock_t` and
`r_t = drift + X_t`. Therefore the conditional mean given the previous observed
return is `phi * r_(t-1) + drift * (1 - phi)`. `oracle_sharpe` instead passes
`phi * returns.shift(1)` to its sign strategy, omitting the intercept even with
the nonzero default drift 0.0003. Its docstring calls this the conditional mean
and the best causal sign strategy.

At phi +0.3 and previous return -0.0005, the reference predicts -0.00015 while
the true conditional mean is +0.00006. At phi -0.3 and previous return +0.0005,
the reference predicts -0.00015 while the true mean is +0.00024. Both choose
the opposite sign. Independent 128-bar source-only probes at seed 2026100800
find three disagreements among 126 paired lagged observations for each phi.

This affects the oracle's claimed effect size and capture/detectability reading,
not the unmodified search or composite/ADR-018 detection counts. A
population-optimal sign rule also need not maximize a realized sample's Sharpe:
in the bounded probes the reference's sample Sharpe happens to exceed the
drift-aware rule's. Do not infer sample superiority from the theoretical label.

## Current reporting boundary and next correction

Fixed local power controls may run unchanged, but report existing gross/net
outputs as the historical **reference sign strategy**, not the true conditional-
mean optimum. Qualify capture/frontier narratives that rely on that label.
Do not silently repair or relabel generated historical artifacts.

A future correction needs a separate ADR and RED drift-aware sign tests,
explicit oracle-method attribution for historical/new power measurements, and
review of gross versus cost-aware/net interpretation. This finding does not
authorize a threshold change, data rewrite, workflow dispatch or paid resource.

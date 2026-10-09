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

## Display mitigation (methodology remains Open)

`GatePowerPanel` currently labels AR(1) scores "Oracle Sharpe" and "Oracle net
of costs". Its shared caveat calls capture a fraction of available edge and
claims a near-zero net oracle means the planted edge was never there to be
found. A fixed sign reference, particularly one omitting conditional drift,
cannot justify that absence-of-tradeable-edge claim.

The display-only mitigation names AR(1)'s historical reference sign
strategy and explicitly disclaims conditional-mean optimality and a realized-
sample maximum. Capture is described relative to the stated reference, and
a near-zero net reference is identified as an unstable ratio denominator,
not proof that no tradeable edge exists. Band-reversion labels, all served
scores and detection counts, payload identities, stored artifacts and
thresholds remain unchanged. This clarification does not repair the oracle
method or close this finding.

Verification: two new AR-only/mixed-sweep assertions failed against the original
panel before implementation; the band-only preservation test passed. After the
wording correction, all 17 focused panel tests pass, including unchanged served
scores, detection counts, null ratios and band-only labels. Targeted ESLint and
`git diff --check` pass. Session17 full `make check-all PYTEST_WORKERS=4`
passed 3,163 backend and 359 frontend tests; independent research and frontend
reviews approved the mitigation.

The follow-up contract clarification removes the same optimality claim from
`oracle_sharpe`'s docstring and the no-achievable-edge conclusion from current
validation cold memory. Even the drift-aware conditional-mean sign rule would
not establish cost-aware or realized-sample Sharpe optimality. Executable
function ASTs are unchanged after removing docstrings; reference arithmetic,
legacy attribution and search/gate identities remain unchanged. Accepted ADRs
retain their historical wording, read with this finding's qualification.
Capture-property docstrings now describe their actual denominator refusals as
ratio limits rather than proofs of no edge. Cold memory also attributes capture
above 100% to selection against a fixed reference, not to AR-state observability.
These are contract clarifications; the oracle-method correction remains Open.


## Additive source-law reference (ADR-223)

A separately named ar1_conditional_mean_sign_sharpe helper now requires explicit
known-law phi and drift, forms phi * lagged_simple_return + drift * (1 - phi),
and delegates to the established generic scorer without another lag. The first
unavailable observed lag stays flat. Its original law/cost parameters and derived
predictions must be finite; no drift is fitted from future or full-sample prices.

This additive function does not change oracle_sharpe, measure_power, persisted
reference identities, API/UI behavior or any historical power measurement.
FINDING-155 remains Open until a separate production opt-in unit supplies explicit
method/drift attribution across artifacts and consumers. Neither the conditional-
mean sign rule nor its gross/net score establishes cost-aware or realized-sample
Sharpe optimality. Source-law provenance remains the caller's responsibility.

TDD observed 45 failing cases before the helper existed; the same 45 pass after
implementation, including both recorded opposite-sign examples, phi zero/nonzero
drift, exact zero-drift historical equivalence, first-lag and causal-prefix
checks, scalar turnover accounting and a bounded independent Hypothesis oracle.

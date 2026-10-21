# FINDING-285: Small-confidence Sharpe intervals lose central Gaussian mass

- **Date:** 2026-10-21
- **Status:** Resolved by ADR-337
- **Scope:** sharpe_confidence_interval central Gaussian quantile

## Evidence

The complete finite source pd.Series([-0.01,0.01]*126) has 252 observations,
Sharpe 0, history 1 year and model SE 1. At accepted confidence 1e-20, the actual
interval is [0,0]. The quantile's expression norm.isf((1-confidence)/2) rounds
its argument to 0.5. Correct bounds ±1.2533141373155004e-20 are representable;
their forward Gaussian central mass erf(z/sqrt(2)) is 1e-20.

At confidence 1e-16, the actual upper bound 1.3914582123358836e-16 implies
central Gaussian mass 1.1102230246251565e-16, about 11% relative excess.
The central inverse-erf quantile gives 1.2533141373155005e-16 and forward
mass 1.0000000000000001e-16. Confidence 2**-1000 also collapses despite
representable nonzero bounds. Parent and independent deterministic probes
confirm these supplied-source results without searches, providers or cohorts.

## Meaning and limits

ADR-184/FINDING-118 already defer very small confidence. These witnesses
concretize that limitation and distinguish quantile cancellation from endpoint
rounding. They do not allege a near-one regression. Default 95% and the tested
high-confidence branch are unaffected. No actual production occurrence,
affected backtest or historical rate change is established.

Forward Gaussian central mass is a numerical quantile oracle within the
existing iid-normal asymptotic model, not measured empirical confidence-interval
coverage or market evidence. Cadence, dependence and the degenerate constant
convention remain explicitly bounded by existing ADRs.

The proposed central evaluation does not eliminate subnormal quantization:
at confidence 2**-1072, the sampled forward-mass error is one confidence ULP,
roughly 25% relative. Nonzero centers can still absorb below-ULP halfwidths.
No universal correct rounding, uniform relative accuracy or recovery of all
endpoint widths is claimed. No confidence floor or cap is justified.

## Resolution

ADR-337 evaluates sqrt(2)*erfinv(confidence) at confidence<=0.5 and retains
the exact existing inverse-survival expression above 0.5. The branch selects
a numerical representation of the same quantile, not a statistical threshold.
Python-float multiplication retains the quantile bits without adding NumPy
scalar-multiply underflow warnings or strict-policy failures at subnormal
confidence. No error-state context or warning suppression is introduced.
Parent froze 56 high-branch complete-result/short-None controls, SHA256
7a2e873a06bef26c85da6bfa6bef1f04195d8d13bf2c31ad6d651ff83291ba1d.
Actual preimplementation TDD recorded 10 failures and 14 controls. Independent
review caught a NumPy product policy regression before publication; supplementary
tests recorded 6 failures and 3 controls before the Python-float correction.
The initial full gate was deliberately interrupted, not reported green.
Final 454 focused tests pass; independent review confirms all 56 frozen payloads,
the prior runtime AST, branch/forward oracles, 3,261 bit-identical product-policy
checks and 27 warning-free interval-policy comparisons. Fresh foreground
make check-all passed 13,647 backend and 566 frontend tests, lint, formatting,
typing and both coverage gates. Source/history checks, Sharpe/SE formulas,
iid_normal identity, API/UI shape, financial thresholds, fingerprints, v14,
generated records and frozen cohorts remain unchanged.

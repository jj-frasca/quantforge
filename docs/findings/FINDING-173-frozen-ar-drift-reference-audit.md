# FINDING-173: Frozen AR conditional-drift reference audit

- **Date:** 2026-10-09
- **Status:** Measured — descriptive source-only comparison
- **Relates to:** FINDING-155, FINDING-168, ADR-223
- **Helper revision:** `5c120b1ee2672fba54fe6bc6fe1d8422744a3474`

## Result

On the exact 800 frozen source laws from FINDING-168, including the known
conditional drift intercept changes reference positions and gross/net sample
Sharpes. These are paired reference-strategy measurements on existing sources,
not new searches, observations, graduation verdicts or a superiority test.

Each cell contains 200 symbols with 7,400 closes, hence 7,398 eligible observed
lag/current-return pairs per symbol. Both rules keep the first unobserved lag
flat. The sign-disagreement count excludes that shared flat startup position.

| Phi | Total sign disagreements | Median disagreements per symbol | Median paired gross Sharpe shift | Median paired net Sharpe shift |
|---|---:|---:|---:|---:|
| -0.2 | 86,698 | 433.0 | +0.031795 | +0.047443 |
| -0.1 | 160,171 | 802.0 | +0.043225 | +0.107290 |
| +0.1 | 131,178 | 658.0 | +0.023266 | +0.065364 |
| +0.2 | 57,791 | 289.5 | +0.012573 | +0.020281 |

Each paired shift is the median of 200 per-symbol new-minus-historical scores.
It is not the difference between the two column medians below.

| Phi | Median historical gross | Median conditional-mean sign gross | Median historical net | Median conditional-mean sign net |
|---|---:|---:|---:|---:|
| -0.2 | 2.532769 | 2.556509 | 1.057428 | 1.088553 |
| -0.1 | 1.252955 | 1.296875 | -0.153060 | -0.056538 |
| +0.1 | 1.292477 | 1.321695 | 0.058664 | 0.132671 |
| +0.2 | 2.595427 | 2.603955 | 1.450056 | 1.479769 |

## Fixed method and evidence

The source law is r_t = drift + X_t, X_t = phi * X_(t-1) + innovation_t.
The historical rule uses sign(phi * lagged_simple_return); the explicit
known-law rule uses sign(phi * lagged_simple_return + drift * (1 - phi)).
Drift is 0.0003, innovation volatility 0.012, centered initial state zero,
initial price 100, native OHLCV geometry, and seeds 2026102000 + i for i=0..199.
The four cells share innovations; they retain separate 200-symbol denominators.

The source-only comparison was chosen before F168 cohort outcomes were read,
as recorded in CODEX_RUNNING_STATE at 2026-10-08 23:04 UTC. Its driver was
independently reviewed before execution. It executed once after ADR-223 was
committed, its exact CI passed and the tree was clean. No drift or parameter
was estimated, selected or fitted, and no additional seed or law was tried.

All 800 source frames matched the four complete source hashes in
[FINDING-168](FINDING-168-v10-frozen-ar-power-grid.md). All 1,600 historical
gross/net scores matched the independently pinned prior reference artifact
exactly, SHA256 `c824558228245f9eda8ad95927ceb3b920a42a60c1c2791da74b2451f3fbb535`.
Independent return division, reparameterized conditional means, sign positions,
entry/flip turnover and sample standard deviation verified every new gross/net
score within 1e-12 absolute/relative tolerance. The net cost remains 0.001 per
unit turnover; annualization remains sqrt(252), with sample ddof=1.

The complete result SHA256 is
`bd313d9b555954005b7be26dd521e203701d966e491c4b242ec27dcac6e81f30`.
Scratch plan, 800 per-symbol rows and summary are under
`/tmp/qf-s21-ar-reference-audit`; driver is `/tmp/qf-s21-ar-reference-audit.py`.
Scratch retention is not guaranteed; reproduce from the stated source laws,
seeds, helper revision, historical scorer and hashes.

## Interpretation limits

Positive median score shifts in these frozen cells are descriptive. They do not
certify cost-aware optimality, a realized-sample Sharpe ceiling, market power,
statistical superiority or absence of tradeable edge when a reference is near
zero. Neither time-bar disagreement counts nor the four correlated arms are
independent observations to pool into an inferential sample.

FINDING-155 remains Open for production method/drift attribution. Historical
oracle_sharpe, measure_power defaults and F168 search-result meanings remain
unchanged. No search, candidate probability comparison, gate re-judgment,
threshold change, workflow dispatch or generated data rewrite occurred.

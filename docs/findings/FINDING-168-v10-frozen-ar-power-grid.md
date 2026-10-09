# FINDING-168: Completed v10 frozen AR power grid

- **Date:** 2026-10-08
- **Status:** Measured — fixed synthetic controls; thresholds unchanged
- **Procedure:** `verified-zero-v10`, full catalog, production refinement
- **Search revision:** `29b7022828861dea15ed38e7ffcc033834b29d62`

## Result

The frozen four-cell grid completed with exactly 200 successfully searched
symbols per cell, zero errors and no dropped or replaced observations. Detection
and ADR-018 survival are different events: at phi -0.2, 117 symbols graduate but
53 survive the universe bar; at phi +0.2, the corresponding counts are 73 and 51.
Both phi -0.1 and +0.1 cells have zero graduates and zero survivors.

Each interval below is a marginal, two-sided 95% Clopper–Pearson interval for
that event under the stated synthetic source law and unchanged procedure.
These are not simultaneous intervals or market-power bounds.

| Phi | Graduates / 200 | Detection rate (95% interval) | ADR-018 survivors / 200 | Survival rate (95% interval) |
|---|---:|---:|---:|---:|
| -0.2 | 117 | 58.50% (51.34–65.41%) | 53 | 26.50% (20.52–33.19%) |
| -0.1 | 0 | 0.00% (0.00–1.83%) | 0 | 0.00% (0.00–1.83%) |
| +0.1 | 0 | 0.00% (0.00–1.83%) | 0 | 0.00% (0.00–1.83%) |
| +0.2 | 73 | 36.50% (29.82–43.58%) | 51 | 25.50% (19.61–32.13%) |

For zero/200 the unrounded two-sided upper endpoint is 1.827534035513624%.
It must not be confused with the 1.4867039% one-sided 95% bound used for the
separate Student-t5 Type-I control in [FINDING-163](FINDING-163-v10-student-t5-null-cohort.md).
Survival uses incumbent passage and strict holdout Sharpe greater than the
ADR-018 bar at N=200 and each record's 1,480 holdout bars; the common bar is
1.3432393159670402. It is not a further candidate-probability verdict.

## Fixed procedure and operational replay

Session 17 registered the original source-only grid before searching it:
phi -0.2, -0.1, +0.1, +0.2; `EDGE0000` through `EDGE0199`; 7,400 bars each;
seeds `2026102000 + i`; drift 0.0003; innovation volatility 0.012; centered
initial AR state zero; initial price 100; native independent OHLCV geometry.
The four cells share innovations. They are not independent arms to pool.

Original session-17 searches were interrupted around attempt 34–35 without
complete results. The session-19 operational replay began at
2026-10-08T22:20:38 UTC in exclusive scratch roots. Before search, it verified
all original procedure fields and complete source digests. Original source
revision was `f888f8f7f2f8732498133084bdfbcb66da521be5`; the replay loaded
`29b7022828861dea15ed38e7ffcc033834b29d62`. Relevant generator, reference,
search and measurement executable methods were unchanged. Later evidence-guard
commits do not retag these already loaded searches.

Each replay retained all 34 registered catalog families, `n_per_param=3`,
GateConfig's 200-trial budget, `refine=True`, `refine_span=0.25`, observed
finalist selection and the native 0.001 cost rate. A neutral 9,000-second
budget was fixed before search. No redraw, omission, tuning, threshold change,
extra look or data rewrite occurred. Replaying the same sources adds no
independent observations: the denominator remains 200 per arm.

- Search identity: `969dd54dd031779c97940ffbc94ebcb47a0d6dee0d66ef2a5b225abf8b6b8893`
- Gate identity: `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`

All four processes exited zero after the driver's final complete/ordered/history/
fingerprint assertions. Outcomes were not inspected until all four succeeded;
complete primitive, source/reference and schema audits preceded interpretation.

## Component attribution

Every count has denominator 200; components overlap and must not be multiplied
as independent probabilities. Canonical joint records, rather than these
marginals, establish the composite counts above.

| Phi | DSR | PBO | Stability | MinTRL | Holdout | Beat buy-and-hold |
|---|---:|---:|---:|---:|---:|---:|
| -0.2 | 151 | 200 | 162 | 200 | 200 | 189 |
| -0.1 | 1 | 175 | 52 | 20 | 133 | 26 |
| +0.1 | 4 | 188 | 157 | 52 | 140 | 54 |
| +0.2 | 84 | 200 | 184 | 200 | 200 | 195 |

Passing an individual component does not establish joint passage. The weak
cells have some DSR passers yet no composite graduate; zero power cannot be
explained as literally zero marginal DSR passage in these cells.

## Reference scores and interpretation limits

These gross/net scores are the historical `sign(phi * lagged_simple_return)`
reference, which omits the conditional drift intercept
([FINDING-155](FINDING-155-ar1-reference-oracle-omits-conditional-drift.md)).
They are not conditional-mean optimality, cost-aware optimality or realized-sample
Sharpe ceilings. The selected finalist score is in sample, across every searched
symbol; no graduate-only conditioning is used.

| Phi | Median gross historical reference | Median net historical reference | Median selected in-sample finalist |
|---|---:|---:|---:|
| -0.2 | 2.532769 | 1.057428 | 1.395329 |
| -0.1 | 1.252955 | -0.153060 | 0.512462 |
| +0.1 | 1.292477 | 0.058664 | 0.600894 |
| +0.2 | 2.595427 | 1.450056 | 1.592021 |

A near-zero or negative net reference does not prove no tradeable edge exists.
These stationary, always-on controls do not bound power against unmatched real
markets, changing regimes or other alternatives. None of these observations
licenses threshold relaxation.

The earlier strong phi +/-0.3 controls used seeds `2026100800 + i` and are
reported separately in [FINDING-162](FINDING-162-v10-fixed-ar-power-cohorts.md).
Thus a six-point display is not a wholly paired experiment; no independent-arm
pooling or directional significance claim is made here. ADR-102's candidate
DSR comparison remains unreadable without matched bootstrap:SPY evidence;
no candidate decision is inferred from this grid.

## Audit and reproducibility

Independent source reconstruction rebuilt all 800 native AR/RNG/OHLCV frames
without production helpers and matched the original four source hashes. Its
pinned reference artifact SHA256 is
`c824558228245f9eda8ad95927ceb3b920a42a60c1c2791da74b2451f3fbb535`.
All 1,600 historical gross/net reference scalars match completed results exactly.

Independent primitive and supplemental audits checked 800 ordered joint records,
zero errors, genuine booleans and finite scores, component conjunctions/counts,
strict per-record survival, exact histories and advertised summaries/hashes.
Current authoritative PowerCalibration parsing and semantic JSON round-trips
passed unchanged, including the subsequent ADR-222 reconciliation guards.
Independent review separately confirmed all counts, references and marginal
intervals before report delivery.

| Phi | Complete source SHA256 | Complete result SHA256 |
|---|---|---|
| -0.2 | `c6859f13fdac26c58e2b58fdf20bb46fb04c4495545ed52dc4bdeb824b6e7ea7` | `1a611bbae7f9d7297a6c57dccb9d1e9dfe9b5b1e99a8317e612083fbf53d14d1` |
| -0.1 | `9b765dc08091e2170e04efdad553a2cfcb454bf1004d1cdd0047e1faa9a2ab94` | `883077af936b3a5f0682eef76f4daf06932339be221cecb93c89981d6ff33321` |
| +0.1 | `9a0d81b61d1276bfe1315ae0c221cb8145132cdab3c6f1c5e9afc5feeace6fa1` | `6e3e45202fb423a53008b04ad1092e92f877336e23034496227f044c2e40ad0f` |
| +0.2 | `36184e919e934f3c5fed9a7ebed74b40d39a404c2ca12f43fdfc8f671e2e6a92` | `1fa866f37c040b8c66079aafd80904825c674821e109fe944f03d973a0fabdce` |

Scratch evidence is under `/tmp/qf-s19-power-curve-CELL-v10` (plan, source digest,
result, summary and primitive audit), with independent reference and complete
schema audits under `/tmp/qf-s19-*audit*`. Scratch retention is not guaranteed;
reproduction must use the stated revisions, source laws, seeds and procedure,
not current catalog defaults or inferred historical measurements. No generated
`data/*.json`, workflow, API key, paid API or cloud run was used or changed.

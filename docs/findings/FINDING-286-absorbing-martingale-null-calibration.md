# FINDING-286: Absorbing integer-price martingale null calibration

- Status: measured — complete fixed cohort; zero observed events
- Protocol: ADR-338 (published before source draw)
- Executed revision: `75bddc05d0be29171cd03da286da8c9705c0123c`
- Scope: one new fixed local N=200 cohort, 7,400 bars per source

## Question and method

The existing completed Gaussian and Student-t5 controls do not measure a discrete
state-dependent-variance price law with absorption, exact ties and a flat suffix.
ADR-338 prospectively fixes P0=128, symmetric integer ±1 until absorption at 1,
PCG64 seeds 2026102107000+i for i=0..199 and one full 7,399-bit draw per source.
All original paths are retained. Ideal next simple returns have conditional mean
zero; binary64 price-ratio rounding remains explicitly qualified.

The unchanged full 34-family search uses default GateConfig/budget 200,
n_per_param=3, refinement/span 0.25, observed selection, prior_trials=0 and no
ExperimentStore. Search/holdout are 5,920/1,480 bars. Each original Experiment and
one-symbol calibration shard is retained, with a durable START before each call.
The single 7,200-second soft admission clock cannot renew; an admitted call may
finish afterward. No retry, fresh continuation, redraw, replacement, source repair
or incomplete-prefix rate is permitted.

## Identity and presearch evidence

- Published protocol commit `75bddc05d0be29171cd03da286da8c9705c0123c`; exact CI 39597102510 and pre-commit
  39597102526 succeeded before the original draw.
- Frozen metadata SHA-256 `dfe63e24d776c8c155fdcfbcb749093df44c5e2539091b7f642a95f302d5ceac`.
- Full tracked backend/app content identity `9a25e3e11c428ebaf2f2389dd2c1d2b1a93fce826d9e43b9c89c423a6c3dda0a`.
- Search fingerprint `edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459`; gate fingerprint `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
- Runner `cc152e59a9ba123c915f2f470e9cd5d2b4fd5c6b6a02d5d2b1bfe64657d3175c`; new helper `3e1b4df82692390922a6713ad5b287e24eb5e40c314fa8d648a831aa2b8ba1c1`; protocol `e8dc6a8b68c374384a8a9a3c04dfb54e697e318f6602a784af08679eacd4314f`.
- Archive `4e7b38f12f5a4ecbec79960de0db9f2f8f666121eb2811944c738ed8f2e857e5`; ordered original-source aggregate `4a1f50dde41c2a9ba981fe2e2ca364f2fa87670956db602d8dc4de51af4f278f`.
- Independent presearch receipt `6c0516288311449b80a98793f5b29ff5d6533583c92d14fe81f0b1f145e69e12` certifies all 200 exact seed/law,
  source/calendar/hash, code, environment and settings identities with zero searches.

The 41 controlled runner tests include 20 Hypothesis bit-pattern examples;
16 inherited helper and 15 additional independent helper controls passed. Six
retained ADR-316 checkpoint function ASTs are unchanged. Four new design-drift
controls failed before the scratch runner's three preflight assertions. Independent
auditor controls observed 13 missing-implementation errors before implementation,
then 20 passed (seven postimplementation controls). Only REVISION assignment
literals changed when binding the tested runner/auditor to the published code.
Exact binomial arithmetic and a 7,525-state Fraction oracle verify the protocol's
analytic design probability and disclosed native rounding bound without draws.

## Result

All 200 original searches completed in one invocation in 2,269.958704556804
seconds (about 37 minutes 50 seconds), with zero errors. Independent final audit
passed in 7.294 seconds, including every original source, START, Experiment and
shard, canonical coarse/refined configuration counts and membership, first
observed-max finalist, selected fixed-configuration holdout replay, joint gate
predicates, official merged result and diagnostic denominator identities.
No raw candidate return-matrix rescan is claimed.

| Endpoint | Events / original sources | Observed rate | One-sided 95% exact upper bound |
|---|---:|---:|---:|
| Graduated | 0 / 200 | 0% | 1.4867039231% |
| Strict ADR-018 survivor | 0 / 200 | 0% | 1.4867039231% |

The strict combined-N200 bar is **1.3432393159670402** at 1,480/252 holdout years.
Survivors were recomputed with unmodified `merge_calibrations`, not summed from
one-symbol shard counts. The largest stored family-finalist selection-adjusted
Sharpe margin is **0.011131700141837175**; this is not the probability-form DSR.

Selected-finalist component pass counts, each over the same 200 sources:

| Component | Passed / 200 |
|---|---:|
| Selection-adjusted Sharpe margin | 1 |
| PBO | 174 |
| Parameter stability | 90 |
| MinTRL | 1 |
| Holdout Sharpe | 76 |
| Beat buy-and-hold | 57 |
| Complete conjunction | 0 |

All five retained diagnostic fields are measured for 200/200 sources: walk-forward
OOS/control Sharpe, purged-CV OOS/control Sharpe, and finalist DSR probability.
Marginal component counts do not determine their joint intersection.

Descriptively, 27 original paths absorbed by the final bar; 19 were already
absorbed at the last search bar (index 5,919). No source was selected, removed,
redrawn or replaced based on absorption. These are source characteristics, not
subset rates or additional hypothesis tests.

Final receipt SHA-256:
`f1daa1e70e378d9d23c7687ef464c4da1eaef5dec62f5e20844a73ffef463158`.
Result SHA-256:
`b989c3c6b3b0959526d9b46d06b1facd6e3cd69a2e585d8f28cda7b17c901d04`.
Summary SHA-256:
`b7a7ee0bb137e95403969ae08f26d4b05f4cef9d74c758f366a095e7c2753f26`.
All original START/Experiment/shard file identities aggregate to
`7fe520d8a91213a060cba71f813f42ba283a514020a3fb448701a56053c62764`.

The frozen environment is Python 3.12.13, NumPy 2.5.4, pandas 3.0.6,
SciPy 1.18.1, Pydantic 2.14.1, yfinance 1.7.0, PCG64, on
macOS-26.6.2-x86_64-i386-64bit. Lockfile SHA-256 is
`081201331ccecf2e93b35e8949fd2b5596312c7130d92df3170d9b01ef8eea72`.
The source uses no vendor calls. Frozen NumPy policy is divide/invalid/overflow
warn, underflow ignore; listed thread environment overrides are absent.

Fresh foreground `make check-all` completed successfully: 13,647 backend tests
(97.38% coverage), 566 frontend tests (97.83% statement coverage), and all lint,
format and type checks passed. Independent written-claims review approved the
finding against the original artifacts; a separate 80-digit Decimal calculation
confirmed the zero-event upper bound. No scientific source changed during review.

## Limits

This complete zero-event outcome has a one-sided 95% exact binomial upper
limit of 1 - 0.05**(1/200), not a zero population-rate guarantee. Graduation and
strict combined-N ADR-018 survival are two endpoints on the same 200 sources,
not 400 independent observations. The universe annotation is not an alpha-level
guarantee. Diagnostic missingness must retain its own denominator. Any source
regime subsets are descriptive only.

This is law-specific local evidence, not market safety, bootstrap calibration,
AR power, general-null robustness or the matched pair required by ADR-102.
Historical frozen incomplete cohorts remain untouched, permanently incomplete
and unpooled. No generated data/*.json, thresholds, estimators, accounting v14,
production source, broker credentials or paid/cloud resources changed.

Scratch artifacts live at `/tmp/qf-w43-s10-v14-absorbing`; retention is not
guaranteed. Exact law, seeds, code, dependency versions and identities support
scientific reproduction, not authorization to rerun this frozen cohort.

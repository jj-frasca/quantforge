# ADR-036: Measure the graduation gate's false-positive rate against a constructed null

- **Status**: Accepted
- **Date**: 2026-08-19
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-014 (graduation gate), ADR-016 (search + trial accounting), ADR-018 (universe
  deflation), ADR-027 (gate calibration)

## Context
QuantForge's entire claim is that its gate is honest: a graduate is not a lucky draw. Every
component of that gate is individually principled and individually tested — Deflated Sharpe for
trial multiplicity, CSCV PBO for selection overfitting, MinTRL for track-record length, a sealed
holdout, a beat-buy-and-hold requirement, and the ADR-018 best-of-N universe-deflation bar on top.

What has never been measured is the **composite**. The gate is a conjunction of six thresholds
applied in sequence to the output of a parameter search, and the false-positive rate of that whole
pipeline does not follow from the individual guarantees. DSR controls trial multiplicity *within* a
symbol; it says nothing about the interaction between "best config by in-sample Sharpe" and "score
that config on a holdout" and "compare it to buy-and-hold." There is no analytic answer for a
composite like that.

The live pool is suggestive but not sufficient. 3,211 experiments over 607 real symbols produced
206 graduate experiments, of which **0** clear the ADR-018 bar (`scripts/pool_report.py`,
2026-08-19). That tells us the bar bites. It does not tell us whether the bar is correctly *sized*,
because real equities may well contain a small real edge — a low graduation rate on real data is
consistent both with a well-calibrated gate and with an over-tight one, and a high one would be
consistent both with real edges and with a leaky gate. The observation is not diagnostic.

The complementary experiment is the one every honest statistical procedure owes: **run the pipeline
on data that has no edge by construction, and count how often it graduates something.** That number
is a measured Type-I error for the system as a whole, and it is the single most auditable claim this
project can make about its own rigor.

## Decision
**Build a null-model calibration harness that runs the unmodified search + gate over synthetic
symbols with no exploitable structure, and reports the empirical false-graduation rate. Change no
threshold in this ADR.**

Two null generators, because the criticism of each is answered by the other:

- **`iid_normal_null`** — returns drawn iid from a normal with a given drift and volatility. The
  textbook null: clean, exactly zero serial dependence, trivially reproducible from a seed. Its
  weakness is that it is *too* easy — no fat tails, no volatility clustering — so a gate could pass
  this null and still be fooled by real market noise.
- **`bootstrap_null`** — an iid resample **with replacement** of a real symbol's own historical
  returns. This preserves the marginal distribution exactly (fat tails, skew, realized drift and
  volatility level) while destroying every serial dependence — autocorrelation, momentum,
  mean reversion, volatility clustering. Every strategy in the catalog trades on serial structure,
  so its true edge on this data is **exactly zero by construction**, and the result cannot be
  dismissed with "your synthetic data was unrealistically well-behaved."

`calibrate_gate` runs the same `run_search` each real hunt runs — same catalog, same grid, same
`GateConfig`, same holdout split — over `n_symbols` null price frames, and returns a
`NullCalibration` recording: symbols tested, graduates, the false-graduation rate, how many
graduates additionally cleared the ADR-018 universe-deflation bar computed at that same `n_symbols`,
and the holdout-Sharpe distribution (max and 95th percentile) so the bar's placement can be read
against the null it is supposed to describe.

The prices are OHLCV frames built from the generated return path, so the harness feeds the real
engine through the real code path rather than a parallel implementation.

### What this is NOT
It is not a threshold change and must not become one by the back door. Charter §4 forbids weakening
a validation threshold to manufacture a graduate, and this ADR deliberately produces the *only* kind
of evidence that could justify a threshold change in the other direction. If the measured
false-graduation rate is materially above the nominal level, that is an argument to **tighten**, in
its own ADR, with this number cited. If it is at or below the nominal level, the gate's honesty
claim is supported by measurement rather than assertion.

## Alternatives considered
- **Permute the signal instead of the returns.** Shuffling the strategy's own signal series breaks
  the signal/return alignment and gives a per-strategy null. It is a fine test but it measures a
  different thing: it holds the return path fixed and randomizes the strategy, so it cannot see the
  interaction between the search's config selection and the holdout. Bootstrapping the returns
  randomizes what the search is searching, which is the failure mode of interest.
- **Block bootstrap** (resample contiguous blocks). Preserves short-horizon serial dependence — that
  is precisely what the strategies trade, so a block bootstrap does not construct a null at all; it
  constructs a weaker version of the original data. Rejected for this purpose. (It is the right tool
  for a *confidence interval* on a real strategy's Sharpe, which is a separate question.)
- **Derive the Type-I rate analytically.** Not available for a conjunction of six thresholds applied
  after an in-sample argmax. This is exactly the situation Monte Carlo exists for.
- **Trust DSR alone.** DSR is the strongest single component, but it is computed on the in-sample
  trial family; the gate then applies a holdout test and a benchmark test whose joint behavior with
  DSR is not characterized. Measuring the composite is the point.
- **Run the calibration inside CI on every push.** A meaningful run is hundreds of full searches —
  minutes to hours. CI gets a small, seeded, deterministic test that pins the harness's *mechanics*
  (a null run completes, the rate is a well-formed fraction, the same seed gives the same answer);
  the large run is a driver script, like every other expensive thing in this repo.

## Consequences
- The project gains a measured, reproducible Type-I error for its whole pipeline, citable from a
  seed. This is the strongest available answer to "how do you know the gate is honest?".
- `scripts/null_calibration.py` is a new expensive local/cloud driver. It writes no pooled data and
  has no vendor dependency in the `iid_normal` mode; `bootstrap` mode needs one real symbol's
  history.
- Null experiments are deliberately **not** written to the research pool. They are not hypotheses
  about a real symbol and must never inflate the MinTRL denominator or appear on the leaderboard.
- The result is a property of a specific `GateConfig`. Re-run it whenever the gate config changes —
  that is the point of having it.

## Reversal
Delete `app/research/lab/calibration.py`, its test, and `scripts/null_calibration.py`. Nothing in
the hunt, the gate, the pool, or the paper book reads any of it — the harness is purely a measuring
instrument pointed at code it does not modify.

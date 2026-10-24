# ADR-358: Preregister one persistent-variance integer martingale null

- **Status:** Accepted — prospective protocol, no measurement yet
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session 26, ISO 2026-W43; independent research review
- **Extends:** ADR-036/037/044/338
- **Relates to:** ADR-046/048/050/316, FINDING-241/243/267/286

## Question and alternatives

Does the unchanged default longitudinal search/graduation procedure produce false
graduates under an ideal zero-conditional-mean price law with independent persistent
stochastic variance states? ADR-338/F286 measures constant integer innovations
with price-dependent variance and absorption; it does not measure independent
persistent volatility states. ADR-316/F267's deterministic variance schedule is
permanently incomplete. This distinct question is neither its replacement nor a
continuation, retry, extension or pooled denominator for any frozen cohort.

Choose one separately prospective persistent-amplitude martingale cohort. Keeping
only completed controls leaves this specific stress unmeasured. Reflection,
conditioning on survival, searching pilot paths and replacing failed attempts
would change the law or select the answer; they are prohibited. An unbounded
innovation law risks nonpositive wealth. A positive absorbing floor and bounded
symmetric increments preserve an ideal no-directional-edge law without redraws.
The cost is local compute and a single-use execution that might remain incomplete.

## Fixed source law

Exactly N=200 original sources, each 7,400 bars and 7,399 innovations. Source i
uses NumPy default_rng(2026102407000+i), i=0..199, requiring PCG64. Make exactly
two calls in this order:

1. `integers(0,2,size=7399,dtype=np.int64)` for signs (0=-1, 1=+1).
2. `integers(0,50,size=7399,dtype=np.int64)` for state flips (0=flip, 1..49=stay).

Draw both full arrays, including unused absorption suffixes and the last flip.
The initial integer price is P0=384, absorbing floor128, initial amplitude state
S0=1. For innovation j=0..7398, use the CURRENT state: a=min(Sj,Pj-128), then
Pnext=Pj+sign[j]*a. Store the new price. AFTER that step, set Snext=5-Sj if
flip[j]==0, otherwise Snext=Sj. Thus the first increment has amplitude1 and the
first flip affects the second increment. At floor128 prices stay flat forever;
state transitions and the prescribed draws are not stopped or conditioned.

The ideal sign and flip streams are independent. State is not exposed to the
strategies, although past price changes may reveal its realized amplitude. Given
the pre-sign information, symmetric signs imply zero conditional mean increment;
the tower property gives E[next simple return | observed price history]=0. A
bounded predictable lagged position has zero expected next-bar gross simple P&L;
nonnegative turnover charges cannot create positive expected net return. Away
from the floor cap, high-state innovation variance is16 times low-state variance,
and the ideal mean state spell is50 steps. Initial low state is fixed, not sampled
from a stationary distribution. This is not iid returns, zero log drift, a claim
that volatility state is perfectly known in advance, or a finite-sample Sharpe
or false-graduation guarantee.

Integer prices lie in [128,29980], hence are exact Float64. The bound on absolute
ideal simple returns is1/33. These finite bounds do not certify every downstream
indicator or estimator operation. Native price-ratio-minus-one is not an exact
numerical martingale: deterministic Fraction enumeration of29,852 active integer
prices times two states (59,704 pairs) bounds this operation's absolute paired
conditional-mean rounding error by2^-54. Price131/state1 gives -2^-54 and
price134/state4 gives +2^-54. All production arithmetic remains unmodified.

Symbols V14PVAR26_0000..0199. Published seed-number references and retained frozen
metadata have no intersection with this range; historical scratch retention is
incomplete, and distinct seeds do not prove mathematical PRNG stream independence.
Use generic business-day UTC labels starting2000-01-03, explicit ns resolution.
open0=close0; open[1:]=close[:-1]; high=max(open,close); low=min(open,close);
volume=1,000,000. Column order open,high,low,close,volume. No market, intrabar,
holiday, liquidity, volume, vendor or exchange-calendar realism is claimed.

## Publication, identity and exclusive execution

Publish this protocol and verify its exact master CI BEFORE any actual source
draw. Controlled fake-RNG/search tests must pass first. New scratch runner:
`/tmp/qf-w43-s26-v14-persistent.py`; exclusive root:
`/tmp/qf-w43-s26-v14-persistent`; helper:
`/tmp/qf-w43-s26-persistent-common.py`. Copy the retained ADR-338 generic helper
bytes and audited observer/checkpoint/budget machinery without changing old
scripts, sources, markers or results. No absent historical artifact is recreated.
Only law/identity-specific generator, membership validation and constants change.
An independent auditor must retain the existing full Experiment/selection/holdout/
joint/count audit while independently reconstructing this new source law.

Before search, bind final runner/helper/protocol bytes, full backend/app source,
published protocol-bearing revision, dependency/RNG versions, default full
catalog/resolved grids, gate/search fingerprints, source law/seeds and source,
calendar/column/archive aggregate identities. Require all34 families, default
GateConfig/budget200 and accountingv14. Execute at that published revision,
unchanged throughout execution. Only the REVISION literal may change from the
controlled prepublication executable; audit its entire AST when binding. Retain
no inherited drift/vol metadata. No production search, estimator or threshold edit.

Freeze all200 original sources exactly once. Local source_valid proves only
step membership, initial amplitude, floor suffix, exact integer bounds and OHLCV
geometry. Independent presearch audit must validate ALL200 exact seeds, two-call
order, full state/sign replay and every source/calendar/hash byte, plus settings,
code/environment identity, with zero searches. It exclusively writes a receipt
bound to metadata/archive/ordered-source/protocol/runner/revision; run refuses
absent or partial evidence. Deterministic reconstruction is an equality check,
never replacement files. Any draw/source/audit failure aborts permanently without
repair, redraw, seed substitution or a replacement attempt.

Use unmodified calibrate_gate once per source, custom mode
`persistent_variance_integer_martingale_v14_session26`, all34 canonically ordered
catalog names, default GateConfig/budget200, n_per_param3, refine=True,
refine_span.25, observed selection, prior_trials0 and no ExperimentStore. The
source has5,920 search/1,480 locked holdout bars (holdout1480/252 years).
The observational wrapper verifies exact call identity, writes START durably
BEFORE each call, and preserves the full original Experiment and one-symbol
calibration shard or error afterward. No synthetic record enters the real pool.

One fresh search invocation has a fixed7,200-second soft admission deadline:
no new source starts at/after it; an admitted call may finish afterward. Record
the clock once after preflight. F286's2,270-second duration supports planning,
not a completion guarantee; reserve final audit/gate/publication margin before
starting. Never renew the clock. Error, unresolved START, interruption or missed
admission leaves this cohort permanently incomplete. Never retry, resume fresh
work, remove markers, redraw, rebudget, repair sources or create a replacement
attempt. Later invocation is all-complete read-only replay only. No partial
rates or inferred interruption cause/activity, and no incomplete-as-zero rule.

## Inference, reporting and boundaries

Only all200 original completions, zero errors and passing independent full
source/identity/model/selection/holdout/joint/count audits authorize cohort rates.
Merge official shards through unmodified merge_calibrations and recompute strict
ADR-018 survival at combined N200; do not sum shard survivors. Preserve selected
joint verdicts, component counts and diagnostic missingness/denominators. Report
graduation and survival separately, the strict bar and marginal one-sided95%
exact binomial upper bounds. Zero events gives1-.05**(1/200), not a zero population
rate guarantee. Two endpoints on200 sources are not400 independent observations.
No simultaneous two-endpoint coverage is claimed. Source-regime subsets, if
reported, are descriptive only, never substitute denominators or extra tests.

A false graduate or mechanics failure requires a written finding, never an
outcome-led source/search/threshold change. Do not pool laws, attribute unpaired
differences solely to stochastic variance, certify market safety/general-null
robustness, infer bootstrap behavior or AR power, or authorize a probability gate.
This custom law is not ADR-102's required matched iid/bootstrap pair.

All work is local and free: no keys, paid APIs, cloud resources/dispatch, broker,
generated data/*.json or pool writes, threshold, production estimator or v14
changes. Scratch retention is not guaranteed. Record exact law, seeds, code and
environment for scientific reproduction, without authorizing a cohort rerun.

## Pre-draw verification

Independent prospective research review supports this distinct scientific question,
the ideal-law proof, bounds and narrow derivative mechanics. Parent and reviewer
independently verified all59,704 rounding pairs; namespace checks found no published
or retained frozen seed overlap, with the retention limits stated above.

The copied runner produced23 genuine law failures/33 passing controls before its
new generator/membership/metadata implementation. Two additional N/BARS drift
tests failed before their preflight guard. Final58 controlled tests pass, including
25 controlled-pattern Hypothesis examples; no actual cohort RNG or search is used.
The helper is byte-identical to the retained generic helper. Eleven retained
function ASTs, including observer/budget/run, are exact; freeze differs only in
two law-specific messages. Parent independent review approved these boundaries.

The separately copied auditor produced13 law failures/19 controls before its
independently written shifted-flip-parity reconstruction and law metadata.
Final40 controls pass, including eight postimplementation full-length fake-array
cross-oracles against the runner. Independent reviewer separately ran the initial
32 controls and confirmed twelve retained function ASTs, including the complete
final scientific audit, are exact. Namespace/message/description changes elsewhere
match the declared scope. Metadata dictionaries agree exactly. Both executables
remain unbound, and the exclusive actual cohort root is absent at this stage.

Actual source draw remains forbidden until exact protocol CI is green, revision
binding preserves every AST node except its literal, and the presearch/final
independent audit tooling is ready. These controls are mechanics/design evidence,
not a calibration measurement.

The read-only actual-production preflight found162 tracked backend/app files
and96 imported modules stable before/after settings resolution. All34 families,
budget200, accountingv14 and the existing search/gate fingerprints matched;
default_rng was forbidden, with zero actual sources/searches. Fresh foreground
make check-all passed14,537 backend and731 frontend tests, with97.41%/97.88%
coverage and clean lint/format/types. Only this protocol and the cold-memory
description are repository changes. Final unbound runner/auditor snapshots are
preserved for whole-AST revision-binding checks after publication and exact CI.

## Reversal

Before any draw, cancel with a superseding decision. After freeze/execution retain
every original byte and marker; report complete or incomplete status without
rerunning/replacing. A genuinely different future question requires separate
review and a prospective protocol.

# ADR-338: Preregister one absorbing integer-price martingale null

- **Status:** Accepted — prospective protocol; no measurement yet
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 10, ISO 2026-W43; independent research review
- **Extends:** ADR-036/037/044
- **Relates to:** ADR-046/048/050/316, FINDING-241/243/267

## Question and alternatives

Does the unchanged default longitudinal search/graduation procedure produce false
positives on a zero-conditional-mean price law with state-dependent variance,
exact ties and an absorbing flat suffix? The completed Gaussian and Student-t5
controls do not answer this question. ADR-316's deterministic variance schedule
also differs from absorption. Its incomplete cohort remains permanently frozen;
this is neither its replacement nor a continuation of any prior attempt.

Choose one prospective, independently reviewed absorbing martingale cohort.
Keeping only existing controls would leave this distinct question unmeasured.
Reflection at a positive boundary would introduce conditional drift; conditioning
on nonabsorption or redrawing prices would change the intended law. Retrying an
incomplete AR/bootstrap/heteroskedastic cohort is prohibited.

## Fixed source law

Exactly N=200 original sources, each 7,400 bars and 7,399 innovations. Source i,
i=0..199, uses NumPy default_rng(2026102107000+i), requiring PCG64, and exactly one
`integers(0,2,size=7399,dtype=np.int64)` call. Map0 to-1 and1 to+1. Draw every bit,
including those unused after absorption. Symbols V14ABS10_0000..0199. The namespace
has no repo reference or overlap with retained frozen metadata. No replacement.

Set integer P0=128. At each innovation, set Pnext=Pprev+epsilon when Pprev>1;
otherwise set Pnext=1 forever. Store prices as Float64. Every integer is exact
and lies in[1,7527]. No clipping, reflection, survival filtering or special
handling of flat sources. Retain all200 original paths without selecting for an
observed absorption count.

Under the ideal symmetric law, the conditional mean next simple return is zero:
at state k>=2 returns are +/-1/k; at1 they are zero. Its conditional variance is
1/k^2 before absorption and zero afterward. A bounded predictable position has
zero expected next-bar gross simple P&L; nonnegative turnover charges cannot
create positive expected net return. This is not an iid-return law, a zero
log-drift claim, or a guarantee about finite-sample Sharpe or false graduates.
A deterministic reflection/binomial calculation gives absorption probability
approximately0.139846 by the final bar, a design characteristic rather than an
observed outcome or target count.

Exact price bytes do not imply an exact numerical return martingale. Native
price-ratio-minus-one rounding has conditional-mean errors of either sign;
state3 gives -2^-54 and state6 gives +2^-54. Independent deterministic enumeration
of reachable active states bounds this specific operation by2^-54; this does
not bound all indicator, cost or estimator rounding. The no-edge proof concerns
the ideal law, while the actual unmodified implementation retains its rounding.

Use generic business-day UTC labels starting2000-01-03, explicit ns resolution.
open0=close0; open[1:]=close[:-1]; high=max(open,close); low=min(open,close);
volume=1,000,000. Columns open,high,low,close,volume. No intrabar, holiday, volume,
liquidity, vendor or market-realism claim. Calendar labels are synthetic.

## Publication, identities and single-use execution

Publish this protocol and verify its exact master CI before any actual source
draw. Controlled fake RNG/search tests must pass first. The scratch runner is
`/tmp/qf-w43-s10-v14-absorbing.py`; exclusive root
`/tmp/qf-w43-s10-v14-absorbing`; new helper
`/tmp/qf-w43-s10-absorbing-common.py`. The old shared scratch helper is absent.
Reuse the retained ADR-316 observer/checkpoint implementation, with a separately
tested new identity/serialization helper; do not claim the missing helper was
replayed, recreate old sources or change any older cohort. Scratch absence says
nothing about an interruption's cause or activity.

Bind final runner/helper/protocol bytes, full backend/app code, git revision,
dependency/RNG versions, resolved default catalog/grids, gate/search fingerprints,
source law, seeds, source hashes and aggregate archive/calendar/column identities
before any search. Execute at the published protocol-bearing revision, unchanged
through execution. Only its revision literal may differ from the controlled
prepublication runner; audit its full AST. No inherited drift/vol metadata.

Freeze all200 original sources once. Independently validate all200 source hashes,
full exact seed/law reconstruction, shapes, native finite positive OHLCV,
calendar and metadata before searching. Exclusively write a presearch receipt
bound to archive/metadata/ordered-source/protocol/runner/revision, with200 validated
sources and zero searches. The runner refuses absent or partial audit evidence.
Read-only deterministic reconstruction is allowed, never replacement files.
Any draw/source/audit failure aborts without repair, redraw or a new attempt.

Use unmodified calibrate_gate, once per source, with custom null_mode
`absorbing_integer_martingale_v14_session10`, all34 canonically ordered catalog
names, default GateConfig/candidate budget200, n_per_param3, refine=True,
refine_span0.25, observed selection, prior_trials0 and no ExperimentStore.
Search5,920/holdout1,480 bars, holdout1480/252 years. Persist original Experiments
and one-symbol calibration shards through the observational run_search wrapper.
Verify exact call identity and selected joint verdict; durably record START
before the call and completion or error afterward. No search/gate modification.

One fresh search-phase invocation has a fixed7,200-second soft admission deadline:
no new source starts at/after it; an admitted in-flight call may finish. Record
this clock once after preflight. Published F241/F243 durations near2,300seconds
support planning, not a completion guarantee. Reserve final verification margin.
Never renew the clock. Any error, unresolved START, interruption or missed
admission leaves this cohort permanently incomplete. Never retry, resume fresh
work, remove markers, redraw, rebudget, substitute sources or create a replacement
attempt. Later invocation is all-complete read-only replay only; it may never
start a fresh search. No partial rates, unfinished-as-zero convention, or inferred
cause/activity claims.

## Inference, reporting and boundaries

Only all200 original completions, zero errors, and independent final source,
identity, model, selection, joint-gate and count audits authorize cohort rates.
Merge official one-symbol shards through unmodified merge_calibrations and
recompute strict ADR-018 survival at combined N200; never sum shard survivors.
Preserve full Experiments and diagnostic missingness/component denominators.
Report graduation and survival separately, strict bar, component counts and
one-sided95% exact binomial upper bounds. With zero events, upper=1-.05^(1/200),
not proof of a zero population rate. Two endpoints on200 sources are not400
independent observations. Source-regime subsets are descriptive, never substitute
denominators or additional preregistered hypothesis tests.

A false graduate or mechanics failure needs a written finding, never outcome-led
source/search/threshold changes. Do not pool with other laws, attribute unpaired
rate differences to absorption alone, or claim market safety, general-null
robustness, bootstrap calibration or AR power. This custom null is not ADR-102's
required matched iid/bootstrap pair and cannot authorize a probability gate.

Everything is local and free. No API keys, paid APIs, cloud dispatch/resources,
broker, generated data/*.json writes, pool writes, thresholds, production search,
estimator or accounting-v14 changes. Scratch retention is not guaranteed; report
law/seeds/environment/code identities for scientific reproduction.

## Pre-draw verification

The inherited runner tests observed 36 missing-implementation failures before
implementation. Its new helper separately observed 16 missing-file setup errors
before implementation and 16 passing controlled tests afterward. Session 12 added
four failing controls for catalog-count/budget/accounting drift, then required
the fixed 34-family, 200-candidate and v14 accounting design in preflight.
All 41 runner tests now pass, including a postimplementation Hypothesis property
over 20 controlled bit patterns. The 16 inherited helper tests and 15 independent
additional helper controls pass;
the latter are postimplementation coverage, not claimed as precode failures.
Fake RNG/search fixtures prohibit actual cohort draws/searches throughout.

Independent review confirms exact AST equality of the six retained ADR-316
identity/checkpoint functions, including the observer and one-use budget. The new
helper is separately tested; no missing historical helper was reconstructed.
Independent deterministic binomial arithmetic gives absorption probability
0.1398460344542098989, and exact represented-return enumeration over all 7,525
active states confirms the stated native conditional-mean rounding bound.
These are design checks, not sampled outcomes or a search measurement.

Publication still precedes actual sources. Bind only the runner revision literal
and verify full AST equality against its prepublication bytes before freeze;
independent presearch and final audits remain mandatory. This record does not
claim any actual source, calibration result or false-positive rate.

## Reversal

Before any draw, cancel by superseding decision. After freeze/execution preserve
all original bytes and markers; publish complete or incomplete status without
rerunning/replacing. A different future scientific question needs its own review
and prospective protocol.

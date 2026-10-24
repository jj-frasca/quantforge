# ADR-359: Preregister one deterministic direct-panel timing fixture

- **Status:** Accepted — prospective engineering measurement, no execution yet
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session27, ISO2026-W43; independent research review
- **Related:** ADR-024/036/081/325/358; FINDING-265/272/298

## Context and alternatives

Direct cross-sectional search/graduation lacks its own null calibration.
Longitudinal symbol calibration and ADR-081's equal-symbol longitudinal panel
statistic do not measure that selector. A prospective correlated-vector null is
a separate scientific question; its local compute/storage feasibility is unknown.
Do not draw or search such a cohort merely to discover whether it fits a session.

Choose one explicitly non-null deterministic engineering fixture before any
timing observation. Existing cloud job durations mix vendor latency, different
families, priors and hardware. Repeated benchmarks or a small null pilot could
select a favorable runtime/path. A single predictable fixture avoids null-pilot
outcomes but cannot establish runtime under a later stochastic law. Deferring all
measurement avoids compute but leaves this concrete feasibility gap unresolved.

This decision authorizes no null law, cohort, calibration denominator, probability
gate, threshold, supported PCV recipe or change to production numerical execution.
It cannot continue, replace, redraw or pool any frozen completed/incomplete cohort.
In particular ADR-358 remains permanently incomplete under FINDING-298.

## Fixed fixture and procedure

Exactly one native Float64 close panel, 3,472 rows and 51 columns.
For integer t=0..3471 and k=0..50, calculate with NumPy Float64 broadcasting:

`100 + .01*t + 2*sin((t+7*k)/17) + sin((3*t+11*k)/29)`.

Fix the left-to-right expression order as written. Generic business-day UTC
nanosecond labels begin2000-01-03; columns `XSTIME27_000..050` in that order.
The deterministic trend and oscillations are explicitly predictable, not a
zero-edge law. There is no RNG, vendor data or OHLCV reconstruction. Native
library transcendental rounding is retained, with exact resulting bytes frozen.
Do not change geometry or formula after observing time or any outcome.

Use unmodified run_cross_sectional_search exactly once at the protocol-bearing
published revision: all13 default price-only families, no fundamental maps,
default quantiles(.1,.2,.3), GateConfig/budget200, cost.001, prior0, PBO10,
WF5, PCV5, embargo2. No refinement, ExperimentStore, real pool or vendor access.
The existing splitter gives2,778 search/694 locked holdout rows. Assert126
allocated configs: momentum18 plus12 families of9. No longitudinal fingerprint
or NullCalibration substitutes for this panel procedure.

The _config_returns observer delegates every call unchanged and retains only
call identity/geometry in sealed scratch evidence. Expect126 search-panel
calls plus ONE full-panel selected-config holdout replay,127 total. Separately
observe13 delegated rank_ic calls, without wrapping factories or altering their
stable identity. Reject call/count/source drift, but never branch on a winner,
score, gate predicate, graduation or survival. No numerical option, BLAS,
thread setting, cost or threshold is forced. Saved runtime observations qualify
the executed engineering environment without enabling decay PCV support.

## Publication, execution and controls

Publish this protocol and verify its exact master CI before generating the
actual fixture or making the actual search call. First implement and test a new
scratch runner `/tmp/qf-w43-s27-xs-timing.py` using controlled tiny fixtures and
fake search/observers only. Actual root `/tmp/qf-w43-s27-xs-timing` must be absent
through controlled verification. Bind only its REVISION literal after publication;
verify whole-AST equality against the retained unbound executable. No real
fixture/search occurs in these tests or the publication gate.

Preflight binds the published protocol bytes, runner, full backend/app source,
dependency/Python/platform/NumPy error policy and thread environment, exact
default registry/grid/factory source identities, resolved allocation and default
gate. HEAD and backend/app bytes must remain at that revision through execution.
Require pandas3.0.6/NumPy2.5.4 and observed compute.use_numba=False for the
declared execution environment; refuse drift rather than changing options.

Create the root exclusively once, freeze exact panel values/columns/calendar in
a pickle-free archive, reload and verify exact hash/shape/dtype/calendar/value
equality, then exclusively fsync a START marker before any search invocation.
Existing root or START refuses before fixture creation/search. Any preparation,
search, observer, persistence or validation failure leaves this attempt incomplete;
preserve original bytes and error evidence without retry, repair, fresh continuation,
altered fixture, renewed clock or replacement timing attempt. This is a single
measurement, not repeated warmups followed by a favorable timing sample.

Time the production search with delegating observers and mechanical call-identity
verification overhead using perf_counter;
record serialization separately. Preserve the full original authoritative
CrossSectionalExperiment as SEALED scratch bytes, including unchecked-copy
revalidation and exact serialization roundtrip. Its values and detailed call
identities are not printed, aggregated into research conclusions or used to
choose geometry/budget. Output only elapsed seconds, byte sizes, process maximum
RSS with explicit units, mechanical counts, hashes/identities and planning status.
No endpoint summaries or calibration rates. Verify source/code/environment
unchanged after execution; do not repair failures. Write all outputs exclusively.

## Engineering criterion and limits

Fix `2 * 200 * search_seconds <= 7200` for200 serial future panels: a factor2
safety multiplier, equivalent to an observed search duration<=18seconds. Also
require process peak RSS<=2GiB and
`200 * (close_array_bytes + calendar_array_bytes + serialized_experiment_bytes) <= 2GiB`.
Record sealed observer-evidence bytes separately; this screen excludes future
audit/checkpoint overhead. These are engineering
screens, not validation thresholds or permission to change a null's sample size.
An error, missing/invalid timing, count mismatch or failed bound leaves local
feasibility unresolved. Do not repeat, reduce geometry/N, change the multiplier
or enlarge this ceiling to obtain a pass. No new cohort is authorized by a pass.

Record search-time extrapolation separately from serialization and preparation;
it excludes future source draws, freeze/audits, gates, publication and CI.
Process RSS includes interpreter/import baseline and is a single-process high-water
mark, not a measurement of every transient array or total host memory. The storage
screen is an uncompressed planning estimate, not a guarantee about future artifacts.
Sorting/ties/variance, null paths, thermal/allocator/cache state and hardware can
change runtime/memory. One predictable panel cannot establish a200-panel completion
probability, null runtime distribution, source independence, PIT, false-positive
rate, power, market safety or behavior of fundamental-map/accumulated-prior searches.

Any later direct-panel null needs its own prospective law/proof, justified N,
geometry, budget, bounded memory/transport design and independent full-panel
source/selection/holdout/joint/count auditor before draws. One whole panel is one
sampling unit;51 columns do not multiply the denominator. Existing longitudinal
and frozen evidence retains its identity, with no reruns or pooling.

Everything is local and free: no credentials, paid APIs, billable runners, cloud
dispatch/resources, broker, generated data/*.json, threshold, estimator or v14
changes. Scratch retention is not guaranteed.

## Pre-execution verification

Controlled tests preceded implementation:32 behavioral failures against explicit
NotImplemented stubs, then calendar roundtrip/altered-calendar failures before
canonical reconstruction, a boolean-count failure before original-integer
inspection, and two CLI outcome-message failures before sanitized entrypoint
handling. Final40 parent controls pass, including20 Hypothesis tiny positive
fixture roundtrips. No actual3472x51 fixture, RNG or production search is used.
Initial pytest discovery attempted an unrelated denied temporary directory;
an isolated scratch test root and explicit configuration corrected discovery.

Independent fake observers also exposed imported-module-origin acceptance and
an unallocated127th holdout quantile before their narrow guards. Preflight now
checks actual app module paths against archived source before/after imports;
the observed full-panel call must belong to the allocated configuration set.
All12 independent controls pass, covering exact delegation, unchanged stable
factories, restoration on errors, call order/config refusal, durable START
before fake search and environment-drift failure. The CLI prints only failure
status/type, while original exception text remains sealed. This does not attest
hostile binaries or vendor numerical purity. Actual root remains absent and
the runner remains unbound at publication; exact CI and whole-AST revision
binding remain prerequisites for the sole actual attempt.

Independent final research review approves the protocol and unbound runner
SHA256 `f7df4a413114534dadd30d2f8337e3cd4ccab7f9c6fc1ad3f44a6f59303dd0af`;
receipt SHA256 `af3249a9ad37a1df53314ba3f0f913ac570389ba27a2320c82d96df9abea4bbf`.
An exclusive identical unbound snapshot is retained for later AST binding.
Fresh foreground make check-all passes14,537 backend and731 frontend tests,
97.41%/97.88% coverage, lint, format and strict types. Only this protocol and
its cold-memory notice change in the repository. No actual root/fixture/search.

## Reversal

Before root creation cancel explicitly. After creation retain every original byte
and report complete/incomplete engineering status without retry or replacement.
Do not remove historical readers or alter scientific execution to make timing fit.

# FINDING-299: One direct-panel timing fixture misses its planning screen

- **Status:** Complete engineering measurement; local calibration feasibility unresolved
- **Date:** 2026-10-24
- **Scope:** The single deterministic non-null timing fixture preregistered by ADR-359
- **Governing decisions:** ADR-024/359; relates to FINDING-265/272/298

## Observation and predeclared decision

ADR-359 was published and its exact CI verified before fixture generation or
search. Its sole exclusive attempt completed at executed revision
`3224b81acd75cce2a7e64c1e9a090e5916b8deff`. START was durably recorded at
`2026-10-24T12:44:28.543355+00:00`. Search with delegating observers and mechanical
verification took **20.118507740087807 seconds**; serialization took
0.010829729028046131 seconds.

The fixed screen was `2 * 200 * search_seconds <= 7200`, equivalent to a
single search duration<=18 seconds. Its observed extrapolation is
**8,047.403096035123 seconds**, exceeding7,200. The predeclared planning screen
therefore fails and local N200 direct-panel calibration feasibility remains
unresolved. This is not evidence that completion is impossible, a timing
distribution under a null, or a reason to change a scientific validation threshold.

| Engineering measurement | Observed | Fixed ceiling | Result |
|---|---:|---:|---|
| Factor2 ×200 search-time extrapolation | 8,047.403096035123 seconds | 7,200 seconds | Not met |
| Process peak RSS, including interpreter/import baseline | 164,728,832 bytes | 2,147,483,648 bytes | Met |
| 200 ×(close/calendar array bytes + serialized Experiment bytes) | 291,539,000 bytes | 2,147,483,648 bytes | Met |

The source arrays occupy1,444,352 bytes; its compressed archive is1,286,468 bytes.
The original serialized Experiment occupies13,343 bytes; sealed observer evidence
occupies14,676 bytes separately. RSS is the macOS process high-water reading in
bytes. The storage extrapolation excludes future source/audit/checkpoint overhead;
time excludes preparation, future draws, freeze/audits, gates, publication and CI.
The factor2 multiplier does not supply a measured completion probability.

Preserve the sole original fixture, marker, sealed result and receipts. Do not
repeat, repair, alter the fixture, reduce geometry/N, change the multiplier,
enlarge the ceiling or create a replacement timing attempt to obtain a pass.
No direct-panel null cohort is authorized or drawn. All previous completed and
incomplete cohorts, including F298, retain their permanent restrictions.

## Exact question measured

One explicitly predictable non-null Float64 close panel,3,472 rows ×51 columns,
generic business-day UTC/ns calendar starting2000-01-03, ordered synthetic
`XSTIME27_000..050` symbols. For integer t=0..3471 and k=0..50:

`P[t,k] = 100 + .01*t + 2*sin((t+7*k)/17) + sin((3*t+11*k)/29)`.

Native NumPy rounding and operation order follow the published protocol and
retained runner. This is neither a stochastic source law nor a null pilot.
The unchanged default price-only search used13 families,126 allocated configs,
GateConfig/budget200, quantiles(.1,.2,.3), cost.001, prior0, PBO10/WF5/PCV5/
embargo2, no fundamental maps, store, refinement, vendor or real-pool writes.
The split was2,778 search/694 holdout rows. Exact delegated call identities
show126 search-panel return calls plus one allocated-config full-panel warmed
holdout replay,127 total;13 rank-IC calls were separately observed.

The full original Experiment and call identities stay sealed. Authoritative
model validation consumed the result solely to verify representation and
non-outcome procedure metadata. Scores, selected winners, gate predicates,
graduation and survival remain unreported and unused in engineering decisions;
mechanical call identities remain sealed. No scientific outcome selects
fixture parameters, resource ceilings or a later source law. It contributes
zero observations to any calibration denominator.

## Identity and verification

Runtime: Python3.12.13, pandas3.0.6, NumPy2.5.4; observed
compute.use_numba=False. Exact package/platform/thread/error-policy, default
gate/grid/factory identities and all162 backend/app source files are retained
in identity.json. No numerical option, BLAS, thread policy or threshold was forced.
This does not identify a source-reviewed Accelerate DDOT kernel or enable decay
PCV; FINDING-265's linked-reducer limitation remains open.

| Retained evidence | SHA256 |
|---|---|
| Published protocol | `045ddfc7430955eb809ce4da57b54a0245783b1ee9f921c1eb0e17a5c6559691` |
| Bound runner | `c1b60e0436cb78d3860af2c99cf1d63178a76bb4a8ae1193b27792a8964fab0a` |
| Bound independent auditor | `7342cea74034410dadf4549c66825c55d70043b161d47769f16456e45d9690b6` |
| Literal-only AST binding receipt | `1717e55392788f26e42d9e5fc38ee350bedc2823ffd32a5281fdf16dc9f29362` |
| Exact source values/calendar/column digest | `a2501ac96f6ced1a1b8184372c36bdf5644a940a0b68ee334aba420accb91919` |
| Pickle-free source archive | `7ddf630bce384553f915f12f27acfbfebd4afcc2a889ad00a6a62d91cf383a26` |
| Executed source/environment/procedure identity | `1474922d4e0f6aeac4d986c4b892f80189852a47367ea8cfc9816b6047f8c10e` |
| Original sealed Experiment | `f7a35e12916368a0e8e7f6765cd633ac72d9f97e0d0ac6e8872cce7a2b06f7f7` |
| Engineering summary | `0f72b7837367e404abb0f4e5e7d52e55b0cc9fb5175384ae50330063c4d2dac5` |
| Independent engineering audit receipt | `e7792886c675c3f54c8a7f3100b04ea8d4e90efaf6e039e7609f84bd3e74f094` |

Parent40 controlled runner tests and independent12 observer/provenance controls
passed before publication; their recorded behavioral RED stages and the tiny
Hypothesis properties are in ADR-359. The separately written independent auditor
passed52 controlled tests before actual execution, following24+2+2+5+13 recorded
RED stages. It uses no runner import or search, independently expressing the
formula, identity/grid mapping, timing/storage screens and source digest.
Audit readiness receipt SHA256:
`260b8c6b0773d65ae4bc14572cabfde974eb230f8953c1773708ecd9fa8003eb`.
Both scripts' whole ASTs matched their retained tested unbound snapshots except
for the single REVISION literal after exact protocol CI succeeded.

The one actual independent audit passed: exact formula/calendar/source hashes,
published code/environment/default allocation, START/identity, all127 call
identities and13IC count, authoritative sealed-model roundtrip and non-outcome
metadata, finite durations and recomputed screens. All seven original artifact
hashes match before/after; its exclusive receipt is outside the root. The audit
checks recorded timing/RSS evidence and arithmetic; it does not independently
remeasure performance or peak memory. Neither original search nor fixture is rerun.

Independent final research review approves this finding and its cold-memory notice,
checking only permitted engineering metadata/receipts, without opening either
sealed artifact. Fresh foreground `make check-all PYTEST_WORKERS=2` passes:
14,537 backend tests (97.41% coverage),731 frontend tests (97.88% statement
coverage), lint, formatting and strict typing. Log `/tmp/qf-w43-s27-check299.log`.
Only documentation changes in the repository.

Root `/tmp/qf-w43-s27-xs-timing`; bound runner is the adjacent `.py`, auditor
`/tmp/qf-w43-s27-xs-timing-audit.py`; external receipt
`/tmp/qf-w43-s27-xs-timing-engineering-audit.json`. Scratch retention is not
guaranteed. One deterministic panel cannot certify stochastic runtime, null
calibration, market behavior, source independence, PIT, fundamental-map or
accumulated-prior searches. No generated data, production code, gate threshold,
accounting-v14 or historical evidence changes.

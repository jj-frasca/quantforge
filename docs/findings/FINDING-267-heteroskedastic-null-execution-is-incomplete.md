# FINDING-267: The ADR-316 heteroskedastic null execution is incomplete

- **Status:** Incomplete execution; no Type-I inference
- **Date:** 2026-10-18
- **Scope:** Local operational evidence for the prospectively fixed variance-schedule control
- **Governing decisions:** ADR-036/037/044/291/316

## Observation

Session 31 published ADR-316, froze all 200 original sources and obtained an
independent all-source pre-search audit before claiming one execution clock.
Session 33 found four START markers, indices 0000..0003, three durable Experiment
checkpoints and three one-symbol calibration shards, indices 0000..0002.
`V14HET31_0003` has no durable completion; 196 sources have no START marker.
There is no error file, combined result, summary or cohort invalidation artifact.
These absences do not establish the cause of missing completion, successful
computation for source 0003 or the original execution's activity state.

The planned N200 cohort is incomplete. No graduation, survival or component
count/rate, interval or full-N Type-I inference is reported from its prefix.
Unresolved and unstarted sources cannot be counted as zeros, failures or
omitted observations. This variance-schedule control remains unmeasured.
Completed F241 iid-normal and F243 Student-t5 controls retain their separate
laws and identities; neither they nor the incomplete AR/bootstrap attempts
are pooled with this cohort.

## Frozen identity and containment

Executed revision `ae77cfc4a4c0b6fb7c926dcae70617e7a96b150e`, accounting v14,
search `edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459`,
gate `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
Symbols `V14HET31_0000..0199` use seeds 2026101809000+i and 7400 bars.
There are 7399 independent Uniform[-sqrt(3),sqrt(3)] innovations per source,
scaled by .005/.04 in alternating 252-return blocks starting low; initial
close100, subsequent closes100*cumprod(1+r). Ideal-law conditional simple-return
mean is zero with predictable variance. Binary64 approximates this law without
certifying an exact numerical martingale. The frozen causal OHLCV geometry and
generic business-day UTC nanosecond calendar follow ADR-316.

The unmodified full34/defaultGate search uses n_per_param3, refine=True/span.25,
observed selection, prior0 and no store; search5920/holdout1480 bars.
The one 7200-second soft admission clock was claimed at
`2026-10-18T12:50:16.499784+00:00`. Subsequent invocation is completed-only
replay; unresolved START and incomplete-cohort guards refuse fresh continuation.
The execution and START fields named `protocol_sha256` bind the frozen metadata
hash below; that metadata separately binds the actual protocol document hash.

| Evidence | SHA256 |
|---|---|
| Ordered source digests | `296373b0822f70c2f9b72b62e9356cbd036b6a7f786e24499ec0073ffd72d37b` |
| Source archive | `046cb8a7ae7c345681543162fb7e7e91e2bbe15a7cee86bc0052c960266a3bfd` |
| Protocol document | `7c73d8dce197c8179bb1cbe3caec30ff16c8126f425831ee8af9cd7924d801a2` |
| Frozen metadata | `40a3122f1aa426eab8b5d22f951e870308ce78b006747062d1c784b69f05f67d` |
| Bound runner | `df2a4e7af99223387e37e2a83a89cae1b159c5dd35fff54579172e96e640db84` |

Preserve every original source, marker, checkpoint, shard, script and receipt.
No retry, redraw, source repair, marker removal, fresh continuation, budget
renewal or replacement attempt to obtain a completed/preferred answer is
performed or authorized. Completed replay cannot supply the missing completion.
No threshold, generated data or production behavior changes.

## Verification and limits

The original independent pre-search receipt is
`/tmp/qf-w42-s31-v14-heteroskedastic/presearch-audit.json`, status
`PASS_SOURCE_ONLY_PRESEARCH`, validated200/searches0, SHA256
`18083df168b24c6b28437787706a7eff06cfec660e452ced2dba412da7e54400`.
It binds source archive, ordered digests, protocol, runner, revision and metadata.

Session 33's separate parent operational audit verified every root artifact's
unchanged bytes, all four exact START/call identities, the three completion
identity attachments, original budget and receipt bindings. The entire current
backend/app tree equals the executed revision's source bytes; the intervening
master arrival changed generated data only. No checkpoint endpoint aggregation,
RNG, runner/helper import, calibration or search was performed by this audit.
Receipt `/tmp/qf-w42-s33-hetero-operational-audit.json`, status
`PASS_INCOMPLETE_ONLY`, SHA256
`a9b52eef8f4bb46eece12bb2480b7b51ece69e103e9b3ef28c879c19a2e2e75a`.

A separate independent read-only preservation audit reconstructed all200 frozen
sources with scalar cumulative arithmetic, verified exact calendar/OHLCV bytes
and canonical hashes, and validated all3 full Experiment/shard models with
lossless roundtrips. It checked saved START attachments, first observed-maximum
selected identity, all six direct gate predicates, MinTRL formula and selected
diagnostic/joint-verdict bindings. All161 tracked backend/app files matched
executed source bytes, and all15 cohort artifact hashes matched before/after.
Deterministic reconstruction was an equality check permitted by ADR-316; no
runner/helper import, search, calibration, replay or cohort write occurred.
Receipt `/tmp/qf-w42-s33-hetero-independent-audit.json`, status
`PASS_READONLY_INCOMPLETE_COHORT_PRESERVATION`, SHA256
`f141dc8ae03048e5637c98434b87d3cdd5d1c6e7b66944290f43f74be6e0ec4d`.
Audit script SHA256:
`96f7aed0ed417de272ba7f8f23590281d0a83abffe04e0ad16c5eff664024f18`.
Independent research review approved this finding and the cold-memory notice.
Foreground `make check-all PYTEST_WORKERS=4` passed: 12881 backend tests
(97.39% coverage), 438 frontend tests (97.69% statement coverage), lint,
formatting and strict typing green. Log `/tmp/qf-w42-s33-check267-final.log`.
No executable behavior or tests changed.

Scratch root `/tmp/qf-w42-s31-v14-heteroskedastic`; bound runner
`/tmp/qf-w42-s31-v14-heteroskedastic.py`. Scratch retention is not guaranteed.
This incomplete control supplies no market-wide bound, arbitrary-schedule
robustness claim, AR power, bootstrap measurement or ADR-102 probability-gate
authorization. Historical generated calibrations keep their executed identities.

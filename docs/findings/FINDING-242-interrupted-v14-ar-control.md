# FINDING-242: Frozen v14 AR control remains incomplete

- **Status:** Incomplete execution; no power inference
- **Date:** 2026-10-14
- **Scope:** Local operational evidence for the new paired strong AR control
- **Governing decisions:** ADR-041/044/291; frozen pre-search protocol

## Observation

The session12 scratch cohort froze 400 sources before searching: 200 at
phi -0.30 and 200 at +0.30, paired by shared innovations. Session14 found
95 durable completed Experiment checkpoints, indices 0000 through 0094,
and 96 started markers, indices 0000 through 0095. The started source
`V14AR12_NEG_0095` has no durable completion. There are no recorded source
error files, arm result files or arm summaries. Absence of an error file
does not establish successful computation for the unresolved source, identify
why durable completion is absent or establish the original execution's activity state.

Neither arm completed its planned N200. This record reports execution
accounting only: no interim detection, survival, component-pass rate,
confidence interval or full-N power claim is calculated. Unstarted and
unresolved sources are not failures, zeros or omitted draws. The completed
prefix is not a replacement cohort, and the positive arm is unmeasured.

## Frozen identity and containment

Executed code `524bf5b78a65245ffbdb35023c7552c3f051e53f`, accounting v14,
full34 search `edb65cb596b9c2daabe2ba81bf5660a562dfc110beefcb16d493244679ad2459`,
gate `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
All sources have 7400 bars, drift .0003, innovation vol .012 and start price100;
pair i uses seed2026101415000+i. Search uses default GateConfig, n_per_param3,
refineTrue/span.25, observed selection, prior0 and no store. The fixed legacy
lagged-sign reference retains FINDING-155's omitted-drift qualification.

Ordered source SHA256:
`b4460194954b985adfda7f6024e8cc69576beec34d8cbe649eaf09c46d0bd54d`.
Archive SHA256:
`d0f7dcedf1dfb7ab57bf1daa8cd8b5c4a7d3c875fb692c498d87fbb8f3d5baef`.
Protocol SHA256:
`907b748f709ee229267af63c1005eaca0e5635b4d438dfb55c3a5aae19340656`.

The frozen protocol prohibits repeating a started incomplete source, skipping
it, redrawing sources or interpreting partial work as a full measurement.
Runner preflight explicitly rejects a started marker without its corresponding
Experiment before any further search. Completed-checkpoint replay cannot
recover missing evidence. This cohort is recorded as incomplete and is not
resumed under its existing unresolved-start rule; its original files remain
preserved. No retry, marker
removal, deadline reset, source generation or new search was performed in
session14. A future measurement requires a separate prospective design, not
silent repair or replacement of this cohort.

## Verification and limits

The session12 independent source audit verified all400 frozen PCG64 laws,
paired innovations, geometry, calendar units, source digests and code/settings
identity before any outcome interpretation. Session14 independently validated
all400 source digests, the preserved artifact hashes, all96 marker identities
and all95 completed checkpoints through the original Experiment validation
boundary with exact evidence roundtrips. The independent receipt is
`/tmp/qf-w42-s14-ar-interruption-research-audit.json` (`PASS_INCOMPLETE_ONLY`).
The original runner's resume preflight was also observed to refuse with
`AssertionError: interrupted source; no blind repeat` before any search.
These checks
establish retained evidence integrity, not completed power calibration.

Scratch root: `/tmp/qf-w42-s12-v14-ar`; original runner:
`/tmp/qf-w42-s12-v14-ar.py`. Local scratch retention is not guaranteed.
Historical frozen v10 measurements and the completed F241 v14 iid control
retain their separate identities. No result is pooled or attributed to a code
change alone. No generated data, thresholds, source law, reference computation
or production code changes in this finding.

Independent research review approved this written scope and its cause/activity
qualifications. Full foreground `make check-all` passed 11,311 backend tests
(97.38% coverage) and 363 frontend tests (97.63% statement coverage), with
lint, formatting and strict typing green. No runtime behavior was changed.

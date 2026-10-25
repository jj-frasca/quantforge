# FINDING-310: PBO interpretation overstates evidence for a profitable edge

- **Status:** Corrected — public PBO interpretation scope
- **Date:** 2026-10-25, Codex autonomous session32 (ISO2026-W43)
- **Severity:** Medium — public interpretation exceeds the reported diagnostic
- **Related:** ADR-105; FINDING-291
- **Affected:** ValidationEngine._interpret, served by POST /api/v1/validate

## Evidence

The low-PBO message says the strategy's edge is unlikely to be a backtest
artifact. PBO measures how the in-sample winners rank out of sample among the
supplied candidates, including tied-winner averaging and the inclusive rank
midpoint. Stable relative ranking need not imply positive performance. The
high-PBO message similarly calls this a probability that the strategy is overfit,
rather than describing the evaluated rank-inversion statistic.

Parent and independent research review reproduced a deterministic HTTP200
counterexample. Fake candidate backtests supply300 observations alternating
[-.001,-.003] for one configuration and[-.01,-.012] for the other. All returns
are negative. Actual PBO, Sharpe, DSR, walk-forward, purged CV, report validation
and API serialization execute; frame acquisition and candidate backtests are
mocked, with unrelated regime classification stubbed. The response reports
PBO0, observed Sharpe-31.69605653705205, margin-84.11662332576813 and passedFalse,
yet says the strategy's edge is unlikely to be a backtest artifact. The client
renders the server's interpretation verbatim. Numerical rejection is correct;
this is a contradictory explanatory claim, not a false graduate or empirical
null-rate measurement. No actual historical report incidence is established.

Probe and receipt: `/tmp/qf-w43-s32-validation-interpretation-probe.py` and
`.log`; independently retained scope/code/consumer anchors:
`/tmp/qf-w43-s32-validation-interpretation-prospective.md`.
F291 corrected other active PBO descriptions but explicitly did not claim
exhaustive cleanup; this reachable response sentence remains a separate residual.

## Correction and limits

Change only the three PBO message tails in _interpret: identify low/moderate/high
frequency of in-sample winners ranking at or below the out-of-sample midpoint
among tested configurations. State in every tier that this diagnostic does not
establish a profitable edge or future performance. Keep the existing thresholds,
verdict enums, interpolation/rounding, all DSR/stability messages, flags, numerical
report fields, public schema, estimators, search/gate policy and v14 identity.

This explanatory repair implements existing rank semantics, with no new
architecture or scientific-method decision. Preserve generated files and frozen
cohorts. It is neither a posterior edge probability nor calibrated pipeline error
rate. Internal repriced-search reports also retain family interpretation strings,
but bounded consumer tracing found no public/persisted use of those strings;
that separate observation does not justify expanding this repair.

## Verification

Seven new regressions failed before the source patch while eight original
interpretation controls passed. Afterward all15 passed, and the focused
engine/report/endpoint suite passed48tests. Independent final research review
approved all five paths and reran the15tests successfully. The tests retain
all display cutoffs and verdicts; the endpoint witness still reports PBO0 and
numerical rejection. Its numeric checks use1e-12 relative tolerance for platform
portability; local prepatch/postpatch preservation is independently exact.

Parent and independent replays preserve the complete prior engine AST except
exactly the three PBO message-tail constants, including interpolation/formatting,
all105 interpretation combinations except their PBO messages, and the complete
mocked HTTP200 payload except its PBO message. All DSR/stability text, flags,
verdicts and scientific values remain exact. Receipts:
`/tmp/qf-w43-s32-pbo-copy-red.log`, `-focused.log`, and
`/tmp/qf-w43-s32-pbo-copy-preservation.log`.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed14766 backend tests
and746 frontend tests; lint, formatting and strict typing passed. Backend
coverage97.42%, frontend statements97.88%. Receipt:
`/tmp/qf-w43-s32-check310.log`. No generated records, thresholds, schema,
scientific calculations or frozen evidence changed.

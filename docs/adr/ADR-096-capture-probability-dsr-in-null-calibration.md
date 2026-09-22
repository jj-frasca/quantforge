# ADR-096: Capture the probability-form DSR per symbol in null calibration

- **Status**: Accepted
- **Date**: 2026-09-22
- **Deciders**: Autonomous session #95 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-036/037 (`calibrate_gate`, `NullCalibration`), ADR-080 (`NullSymbolDiagnostics`,
  the canonical per-symbol pairing this ADR extends)
- **Relates to**: FINDING-007 / ADR-054 (the probability-form DSR is implemented and every new trial
  records it, but the gate still selects on the margin form and "what remains is the threshold
  question — whether the gate should switch to the probability — which needs a fresh Type-I error
  and power curve for the new statistic and its own ADR")

## Context

ADR-054 closed FINDING-007's implementation gap (the paper's probability-form DSR exists and every
new `Trial` records it alongside the margin form) but explicitly left the threshold question open:
switching the gate to the probability statistic needs its own Type-I error and power measurement,
the same class of evidence ADR-050/053 produced for the margin statistic. `PoolReport.
statistic_agreement` (ADR-054) measures how often the two statistics agree **on the real pool** —
useful, but not a Type-I error, since the real pool is not a no-edge-by-construction universe.

Checked this session whether that measurement is even possible from data already committed:
`NullCalibration.symbol_diagnostics` (ADR-080, the canonical per-searched-symbol record) carries
`walk_forward_oos_sharpe`, `purged_cv_oos_sharpe`, and their hold-benchmarks, but not either form of
DSR. `NullGraduate.deflated_sharpe` exists only for the symbols that already cleared the MARGIN
gate — exactly the set a probability-threshold measurement needs to look *beyond*, since a symbol
that fails the margin gate might still pass a probability one. **The finalist trial computed during
every calibration run already carries `deflated_sharpe_probability` (`_finalist(experiment,
select_by).deflated_sharpe_probability`, per `Trial`'s ADR-054 field) — it is simply never persisted
past the run.** Retroactively answering the threshold question from artifacts already in `data/
null_calibration/` is therefore not possible; it needs the field captured going forward.

## Decision

**Add `deflated_sharpe_probability: float | None` to `NullSymbolDiagnostics`, populated from the
same finalist trial `calibrate_gate` already selects for every other per-symbol diagnostic.**

1. `NullSymbolDiagnostics.deflated_sharpe_probability` — nullable, defaulting to `None` so every
   artifact already committed under `data/null_calibration/` continues to validate unchanged (same
   pattern as ADR-080's original fields and ADR-095's `sic_description`).
2. `calibrate_gate` (`app/research/lab/calibration.py`) reads it off the exact same
   `_finalist(experiment, select_by)` call it already uses for the walk-forward/purged-CV fields —
   no new selection logic, no new call to anything, purely reading one more field off an object
   already in hand.
3. **No gate, threshold, or `GateConfig` change of any kind.** This does not touch `dsr_ok`,
   `GateConfig.version_hash`, or any pass/fail logic — it only makes a number visible that the search
   already computes and discards. The threshold question ADR-054 left open still needs its own
   measurement and its own ADR once enough calibration runs carry this field to be worth reading.
4. **No dispatch this session.** Existing `data/null_calibration/*.json` artifacts do not gain this
   field retroactively — same posture as ADR-095: ship the capture capability, let it accumulate on
   whatever `null-calibration.yml` runs next (workflow_dispatch, at whoever's discretion), and answer
   the threshold question from real data once it exists.

## Alternatives considered

- **Backfill existing artifacts by re-deriving the probability from stored fields.** Rejected:
  `deflated_sharpe_probability` needs the trial's track-record length, skewness, and kurtosis
  (ADR-054), none of which `NullSymbolDiagnostics` or `NullGraduate` store — there is nothing to
  re-derive it from. A committed artifact predating this ADR is permanently silent on this statistic.
- **Measure the Type-I error for the probability statistic this session by dispatching a fresh
  calibration run and computing it out-of-band (not persisting the field).** Rejected: a Type-I/power
  measurement for a candidate new gate statistic is exactly the kind of one-shot, decision-shaping
  look this project's culture (ADR-050/053's own rigor, and more recently the panel-null ADR
  chain's insistence on pre-registration before spending a look) says deserves its own ADR stating
  the criterion BEFORE the data is read — not a same-session add-on to an unrelated data-capture
  change. Shipping the capture capability now, without reading anything from it, keeps this decision
  small and reversible while unblocking the real measurement for whenever it is properly scoped.
- **Also capture the margin `deflated_sharpe` per symbol (not just graduates).** Considered — it
  would make a same-session symmetric comparison possible once data accumulates. Left out of this
  ADR's scope to keep the change to exactly the missing piece (the probability form); a future ADR
  can add it in the same low-risk pattern if the eventual analysis needs a per-symbol margin value
  the graduate-only `NullGraduate` list cannot supply.

## Consequences

- `NullSymbolDiagnostics` rows from any future `calibrate_gate` run (local or via
  `null-calibration.yml`) carry `deflated_sharpe_probability`; every artifact committed before this
  ADR keeps validating with the field absent (`None`).
- Unblocks, but does not itself perform, the Type-I-error-for-the-probability-statistic measurement
  ADR-054 named as the open threshold question. That measurement still needs its own pre-registered
  criterion and its own ADR before any gate change is considered.
- No change to any production search, gate decision, or committed artifact's meaning.

## How to reverse

Remove `deflated_sharpe_probability` from `NullSymbolDiagnostics` and the one line in
`calibrate_gate` that populates it. Every artifact — with or without the field — keeps validating
either way (pydantic ignores an absent optional field on load in both directions).

## Measured

Not applicable — this ADR ships capture capability only; see ADR-095 for the same posture applied to
a different field, and FINDING-007/ADR-054 for the measurement this capability is meant to
eventually support.

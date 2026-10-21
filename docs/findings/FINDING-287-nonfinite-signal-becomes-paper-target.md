# FINDING-287: Undefined latest signal becomes a full paper target

- **Status:** Resolved — ADR-339 finite guard verified
- **Date:** 2026-10-21
- **Scope:** `execution/sizing.py::latest_signal`; ADR-021/120/139

## Reproduction

With finite prices and a patched synthetic strategy returning NaN on the last
bar, the existing `min(1.0, max(-1.0, float(last)))` returns -1.0. Passing that
quote through equal-weight sizing gives -100 shares at price 100/equity 10,000.
Independent reproduction at price 8/equity 1,000 gives -125 shares. Positive and
negative infinity become +1/-1 and corresponding full directional targets.
These are deterministic local fixtures; no broker, provider, credentials, source
RNG, search, generated data or frozen cohort is involved.

The conversion creates a direction from undefined strategy evidence. A passed
ResearchDataset carries checked source evidence, not proof that every computed
strategy result is valid.
No actual catalog strategy occurrence, historical paper fill or real-money effect
is established. Direct PositionQuote input validity and signal geometry are
separate contracts; this finding concerns the existing latest-output conversion.

## Correction and limits

ADR-339 retains the original float conversion and finite clamp while refusing a
nonfinite converted last weight with ValueError before clipping. Its unchanged
caller propagates that error before `compute_targets` returns; main consequently
never reaches reconciliation in that invocation. This aborts the whole target
calculation, not a per-symbol skip, zero target, or allocation redistribution.
Existing broker reads may precede target computation; no rollback is claimed.
Main's later equity-snapshot append is also bypassed; this correction does not
reorder account-ledger capture.

Independent scope review reproduced all three nonfinite cases and confirmed 57
finite/typed/signed-zero/subnormal/adjacent-boundary/saturating controls bitwise.
ADR-120's NaN-priced quote still becomes flat and frees its slice. Native float
conversion errors, finite strategy outputs, thresholds and calibration identity
remain unchanged. A wider value whose float conversion is infinite is conservatively
refused; no arbitrary source precision or complete strategy-output validation is
claimed.

## Verification

Before the production edit, the new repository tests produced 16 failures for
nonfinite output and 21 passing controls (2.89 seconds); the backend/app diff was
empty. After the narrow edit, 62 focused synthetic cases passed (2.81 seconds),
including an 80-example Hypothesis finite-weight invariant and three pure
ResearchDataset orchestration refusals. One existing credential-gated live smoke
was skipped; no live broker call occurred. Existing sizing/driver tests were not
edited. Targeted Ruff, formatting and strict mypy checks passed.

A separate parent audit confirms 57 original finite/type return payloads bitwise
against revision2599e59f. The whole prior sizing-module AST is identical after
masking only the declared import, converted-weight binding/guard, return operand
extraction and docstring correction. Runtime SHA-256:
`dcc355770898f4b58a84f566d3023ad5177e37b834e9276ee5dc6d8af5076d75`.
Independent final review approved all five paths. Its fresh focused run passed
62 synthetic tests with the existing live smoke deselected (2.84 seconds), and
independently confirmed all 57 legacy finite payloads bitwise, the final clamp AST
and preservation of unrelated runtime and preexisting tests. Fresh foreground
`make check-all` completed successfully: 13,684 backend tests (97.38% coverage),
566 frontend tests (97.83% statement coverage), and all lint, format and type
checks passed. Runtime bytes remained frozen throughout verification.

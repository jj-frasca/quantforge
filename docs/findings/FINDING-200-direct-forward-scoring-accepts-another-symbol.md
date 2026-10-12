# FINDING-200: Direct forward scoring accepts another symbol

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — direct forward performance can describe the wrong asset
- **Scope:** evaluate_forward target/dataset identity
- **Decision:** ADR-251
- **Prior art:** ADR-139/FINDING-070, ADR-148/FINDING-078

## Evidence

A valid synthetic AAA dataset scored against a BBB paper position returns 277
forward bars and Sharpe -0.9870498368022801, with AAA evidence. A freeze boundary
after all prices also returns a zero-bar score with that mismatched evidence.
Independent reproduction confirms both. Complete PaperPosition attachment rejects
the mismatch, while the standalone scorer returns it before that boundary runs.

The managed paper loop already checks this relationship and leaves a bad-provider
position unchanged. This is a direct-call defect, not an observed bad stored book,
broker order or measured false graduate. No broker, search, cohort, workflow or
generated record was accessed or changed for this reproduction.

## Correction and verification

ADR-251 moves the existing manager symbol comparison into direct scorer entry,
before frame copying and every score shortcut. Independent pre-code review
preserves eight complete native score JSON comparisons across normalized target
spellings and zero/nonzero-forward cases; all 39 existing paper tests pass under
a scratch wrapper.

Before implementation, all three mismatch/frame-access tests failed while eight
matched preservation cases passed. All 123 affected tests pass after the two-line
entry guard. Independent final review approves 85 affected tests, including the
manager fail-soft cases, and 80 exact complete published-baseline score JSON
comparisons across five strategies, four normalized targets, two price paths and
zero/nonzero-forward periods. Position JSON, dataset prices and evidence JSON remain
unchanged. Removing only the guard restores the complete published-module AST.
The full foreground gate passes 5,059 backend and 363 frontend tests, with
97.77% backend and 97.63% frontend statement coverage; lint and strict typing pass.
No new source, quality, position, lifecycle, schema or threshold policy is introduced.

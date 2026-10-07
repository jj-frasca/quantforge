# FINDING-137: PBO discards masked return evidence

- **Date:** 2026-10-07
- **Severity:** Medium — missing observations can produce an apparently passing gate statistic
- **Status:** Resolved — ADR-200

## Evidence

Build a sixteen-row, two-candidate return matrix by repeating `[.01, .02, .03, .04]`
four times for the first candidate and its negative for the second. With four CSCV
groups, the complete matrix returns PBO 0.0. Wrapping those values in a NumPy
MaskedArray with one missing observation or with every observation masked still
returns 0.0. The latter contains no observed returns at all.

The original dtype and finite checks introduced by ADR-189 and ADR-106 operate
after `np.asarray` discards the mask. They validate underlying storage instead of
the supplied evidence. This direct-call reproduction does not establish that the
production return producer emits masked arrays or that a false graduate occurred.

## Correction and limits

Keep the original source until the finite-evidence guard and reject any true mask
with ValueError. An all-false mask is complete evidence and must produce precisely
the ordinary array statistic. Preserve shape, dtype, configuration, split and
history error precedence; do not fill, drop or reconstruct missing returns.
CSCV groups, sample Sharpes, tie ranks, gate threshold and calibration identity
remain unchanged. Extreme finite moment arithmetic remains a separate question.

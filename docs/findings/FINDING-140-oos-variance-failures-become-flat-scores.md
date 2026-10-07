# FINDING-140: OOS variance failures become flat scores

- **Date:** 2026-10-07
- **Severity:** Medium — unmeasurable moments can publish measured-looking diagnostics
- **Status:** Resolved — ADR-202

## Evidence

Both walk-forward and purged-CV evaluation use a scalar native sample-Sharpe
helper with a zero fallback. Repeat `[.01, .02, .03]` four times as one candidate
and its negative as another; train on rows 0–5 and test on rows 6–11, embargo zero.
Both publish mean OOS Sharpe approximately 35.49647870. Scaling the finite matrix
by `1e200` or `1e-200` makes both publish zero instead, without changing the
mathematical Sharpe. Variance overflows to infinity or underflows to zero, and
undefined native moments become fabricated flat scores. Strict NumPy error mode
instead raises FloatingPointError; it does not follow the ValueError contract.

The same helper selects IS winners, scores selected OOS returns and supplied
benchmark blocks. Missing-input guards do not certify native moment arithmetic.
This is a synthetic public-boundary reproduction, not a measured production leak
or false graduate. The normal PBO preflight has separate arithmetic guards.

## Correction and limits

Require measurable finite native mean/dispersion and finite annualized quotient
for every nonconstant nonsingleton block. Reject native zero dispersion for
nonconstant evidence with ValueError under ordinary or strict error mode. Keep
the original one-dimensional moment and multiplication/division order. Do not
rescale, fill or drop returns. Exact constants and singleton blocks retain their
defined zero score. Ordinary finite precision remains a separate question.

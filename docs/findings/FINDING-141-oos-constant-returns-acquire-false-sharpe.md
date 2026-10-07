# FINDING-141: OOS constant returns acquire false Sharpe

- **Date:** 2026-10-07
- **Severity:** Medium — exact flat evidence can publish enormous positive OOS claims
- **Status:** Resolved — ADR-202

## Evidence

Give both evaluators a twelve-row matrix whose every row is `[0.1, 0.3]`, train
on the first six rows and test on the last six, embargo zero. Both publish mean
OOS Sharpe approximately 1.0442137426e17. The first exactly constant column's
rounded mean creates a tiny false positive standard deviation. The second column
scores zero, so selection and the diagnostic both prefer the fabricated score.
A supplied constant benchmark can similarly acquire a false enormous Sharpe.

Actual constant returns have the explicitly defined zero sample-Sharpe convention.
Finite output does not imply measured dispersion. This direct synthetic finding
does not establish an observed production false graduate.

## Correction and identity

Determine exact constant blocks from observations before native moment arithmetic
and score zero. Do not use an epsilon or classify nearly constant returns as flat.
Retain singleton zero and the existing reselection/aggregation contracts.
This changes finite diagnostic values and can change selection, so advance
calibration accounting identity beyond ADR-201's PBO-only correction. Historical
calibration remains readable but cannot match corrected diagnostics. Replacement
distributions are unmeasured; no data edits or calibration dispatch are authorized.

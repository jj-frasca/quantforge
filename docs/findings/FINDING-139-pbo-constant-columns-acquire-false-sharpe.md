# FINDING-139: PBO constant columns acquire false Sharpe

- **Date:** 2026-10-07
- **Severity:** Medium — rounding can move a constant-only matrix across the PBO gate
- **Status:** Resolved — ADR-201

## Evidence

A sixteen-row matrix with every row exactly `[0.1, 0.3]` returns PBO 0.0 using
four CSCV groups. Both configurations have exactly constant returns and should
receive the existing explicit zero Sharpe convention. A matrix with both columns
zero returns PBO 1.0: every tied OOS rank is the median under ADR-105.

For each eight-row half, the native axis-zero mean of the first constant column
is approximately 0.09999999999999999. Its deviations from that rounded mean
produce a standard deviation around 1.4836e-17 and a false Sharpe around 6.74e15.
The second column has zero native dispersion and score zero. The rounded result
therefore invents a dominant candidate from two flat configurations. Unlike the
overflow refusal in FINDING-138, this correction changes a finite returned result.
The reproduction is synthetic and does not establish a production false graduate.

## Correction and identity

Determine exact constant columns from observations before computing moments and
give them score zero. Use unchanged native arithmetic for nonconstant columns,
with ADR-201's measurability refusal. Do not add an epsilon or classify nearly
constant evidence as flat. Advance the calibration accounting identity so old
PBO semantics cannot match the corrected procedure; retain historical artifacts
as historical evidence and do not edit data or dispatch replacement calibration.

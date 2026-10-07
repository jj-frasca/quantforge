# FINDING-129: Margin DSR source and difference are unchecked

- **Date:** 2026-10-07
- **Severity:** Medium — malformed scores or nonfinite derived margins escape a public primitive
- **Status:** Resolved — ADR-194

## Evidence

With valid one-trial accounting and dispersion .2, deflated_sharpe(True) returns 1.0,
deflated_sharpe(inf) returns infinity, NaN returns NaN and complex .2+1j returns a complex value.
Shared accounting and probability PSR source guards do not validate the margin's observed score.
Finite arithmetic can independently overflow: n_trials=2, sr_std=1e308 yields a finite haircut
approximately 5.197553442805938e307, while observed_sr=-1.5e308 yields negative-infinite margin.
Downstream report/Trial finite-field guards protect normal persistence; no corrupt production
record or false graduation is claimed.

## Correction and limits

ADR-194 validates original observed score as finite float-representable real nonboolean evidence
after shared accounting checks, preserving precedence and signed scores; nonfinite native
subtraction raises ValueError. Failing source/output tests preceded the correction, including
strict NumPy mode; signed/numpy/Fraction and one-trial finite oracles protect valid behavior. Keep same nonnegative haircut, estimator, count, dispersion and thresholds. Independent consumer/final review accompanies finite subtraction oracles.
No generated-data changes, arbitrary score caps or methodology redesign are justified.

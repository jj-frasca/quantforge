# FINDING-119: Compounded return helpers coerce nonreal evidence

- **Date:** 2026-10-07
- **Severity:** Medium — malformed source evidence becomes a published return
- **Status:** Resolved — ADR-186

## Evidence

The public total_return primitive converts the source to float64 before source dtype validation.
Boolean [True,False] returns 1.0. Numeric strings ['.01','-.02'] return approximately -0.0102.
Complex [.01+1j,-.02+2j] also returns approximately -0.0102 while warning that imaginary values
were discarded. annualized_return shares _validated_log_returns and the same source coercion.
The existing finite and positive-wealth checks validate the converted array, not original evidence.

## Correction and limits

ADR-186 validates complete finite real nonboolean numeric source Series at both public entries,
before coercion and empty shortcuts. Fourteen failing source-dtype cases preceded the correction.
ADR-110 log-compounding arithmetic, numeric empty zero and the strict >-1 return domain remain.
Independent compounded-wealth oracles protect complete ordinary/nullable samples; consumer review
found no intentional malformed-source contract. No generated record or
threshold changes are justified. Extreme finite arithmetic remains a separate issue.

# ADR-233: Validate present reference prediction evidence

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 22, ISO 2026-W41
- **Resolves:** FINDING-183
- **Extends:** ADR-042, ADR-223, ADR-229, ADR-230

## Context

The shared scorer maps conditional means through sign before validating derived
returns. Infinite predictions become finite positions; complex predictions can
produce real-projected scores with discarded-imaginary warnings. Short-history
shortcuts bypass prediction processing. Missing predictions are an established
flat-startup convention and must remain distinct from malformed present evidence.

## Options Considered

1. Validate original real nonboolean numeric prediction dtype and finite present
   values before short-history/sign processing. This preserves missing evidence
   semantics while refusing malformed supplied expectations.
2. Require complete finite predictions. Simple, but breaks legitimate missing
   startup and sparse coverage, changing historical reference accounting.
3. Check only positions or final returns. Cheap, but sign has already concealed
   infinity and real projection can conceal complex evidence; rejected.

## Decision

After existing cost/source-price checks but before the short-history shortcut,
oracle_sharpe_of requires original real nonboolean numeric conditional_mean dtype.
For validation only, materialize float64 values with missing observations as NaN;
reject positive/negative infinity, including values not float-representable.
All missing predictions, missing startup, sparse matching predictions and missing
labels introduced by existing reindex retain their flat-position semantics.
Validate every supplied prediction, including nonoverlapping labels; invalid
extra evidence is not silently dropped. Preserve the original Series in scoring.

Do not add prediction-index ordering/completeness rules, change reindex/sign/lag/
turnover/cost/native sample arithmetic, require source-law fitting, replace
reference definitions/defaults or alter thresholds/fingerprints/generated data.
This establishes intrinsic present scalar evidence, not arbitrary prediction
causality, calibration optimality or universal numerical precision.

## Verification

Observe infinity/complex/nonreal short and ordinary generic failures before code.
Protect all-missing, nullable, sparse/unaligned, valid numeric means and exact native
scores. Include a Hypothesis scalar sign/turnover oracle for ordinary real means
with missing startup. Independently review producer preservation and run full
foreground make check-all before explicit commit/fresh sync/individual push/exact CI.

## Consequences and reversal

Undefined/nonreal expectations cannot become a real effect-size claim through
sign or a zero-score shortcut. No corrupt artifact or changed detection rate is
inferred. Remove the new source-prediction checks to reverse this decision,
reopening FINDING-183 while retaining the other reference guards.

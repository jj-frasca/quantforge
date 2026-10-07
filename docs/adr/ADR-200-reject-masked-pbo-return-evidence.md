# ADR-200: Reject masked PBO return evidence

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-137
- **Extends:** ADR-106, ADR-189

## Context

The PBO boundary validates original dtype and finite float64 values, but loses
explicit source missingness during array materialization. FINDING-137 shows that
an entirely masked matrix of finite storage values returns PBO 0.0. The mask
identifies unobserved evidence and cannot be silently replaced by storage values.

## Decision

Retain the original performance object. At the existing complete-finite guard,
reject any true NumPy MaskedArray mask with the existing finite-return ValueError.
Keep all earlier shape, dtype, configuration, split and minimum-history checks
in their current order. Accept unmasked arrays, nested numeric lists and masked
arrays whose mask is entirely false, with identical CSCV results.

Do not fill or drop observations, alter group geometry, change scoring or ranks,
relax `pbo_max`, or dispatch calibration workflows. Complete production inputs
are unchanged, so following ADR-106 calibration accounting identity does not
advance. Extreme finite arithmetic and split-count typing are separate contracts.

## Alternatives considered

- Filling masks invents observations and changes the selected procedure.
- Dropping masked rows or columns changes history or the searched family.
- Rejecting all MaskedArrays rejects complete evidence solely for its container.

## Verification

RED regressions cover single, row, column and complete masks on finite storage,
including an all-flat matrix. Complete-mask identity covers the independent CSCV
reference and tied column permutations. Earlier structural errors retain their
precedence. Existing noise, dominant-candidate, reference and tie tests remain.

## Reversal

Discard the source object before the complete-finite guard. That reopens FINDING-137.

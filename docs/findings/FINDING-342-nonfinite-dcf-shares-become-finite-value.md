# FINDING-342: Nonfinite DCF shares become finite value or missingness

- **Date:** 2026-10-30
- **Status:** Confirmed; bounded correction specified by ADR-407
- **Scope:** Latest diluted-share operand consumed by `dcf_intrinsic_value`

At producing revision `3bde88ce`, ordinary AnnualFundamentals permits nonfinite
shares. With one synthetic year, revenue=0, EPS absent, FCF=12 and diluted
shares=+infinity, direct DCF reports intrinsic value per share **0.0**. The finite
numerator divided by infinity erases invalid evidence. `score_valuation(price=10)`
accepts the resulting finite/null record because P/S is inactive and zero DCF
contributes no margin of safety. Negative infinity becomes the normal flagged
unavailable-shares return and also survives composite validation. NaN yields a
NaN direct result; the composite's existing final guard refuses that case.
No actual vendor occurrence, affected graduate, false admission or trading effect
is established. The witness demonstrates validity loss, not a favorable score.

ADR-373 checks final composite output, ADR-401 checks only reached multiple
operands, and ADR-406 checks attempted growth series rather than diluted shares.
None can reconstruct the erased denominator here. A local finite preflight after
earlier base returns and before share eligibility distinguishes invalid evidence
from legitimate missing/nonpositive shares without changing finite formulas.

ADR-407 rejects every present nonfinite latest share operand once that boundary
is reached. Earlier missing/nonpositive base returns, dormant historical shares,
finite shares including signed zero, None and existing growth/error precedence
outside this new refusal remain. Raw base validity, derived arithmetic precision,
unchecked configuration, physical fiscal periods and PIT remain separate.
The new refusal propagates outside provider acquisition fallback: the hunt records
a per-symbol error before search, while a sweep can fail its shard before output.
No catch or partial-success policy is added. No thresholds, generated records,
calibration identities or frozen cohorts change.

Pre-code tests produced 37 failures and 27 passing controls. Six failures were
incorrect multi-year record expectations: quality scoring already rejects those
shares before DCF. Thus 31 original failures target this DCF defect. The first
post-change focused run was 249 passed / six failed, not green. Tests now assert
the earlier Piotroski refusal for those six cases; production was unchanged.
All 64 new cases remain, including the Hypothesis flat-perpetuity oracle.
The corrected focused suite passes 255 tests; independent review approves with
181 tests passing and whole-module AST exact outside the single guard. Its
postimplementation controlled replay of corrected tests against the original DCF
function in memory gives 31 failures / 33 passing controls; this is distinct from
the original pre-code receipt. The bounded replay of 150 ordinary complete outputs
is exact. Full foreground gate and exact publication/CI receipts are tracked in
the ignored session ledger; no pending verification is claimed completed here.

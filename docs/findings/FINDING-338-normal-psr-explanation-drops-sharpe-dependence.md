# FINDING-338: Normal PSR explanation drops Sharpe dependence

- **Date:** 2026-10-29, Codex autonomous session18 (ISO2026-W44)
- **Severity:** Low — incorrect explanation; implemented estimator is correct
- **Status:** Corrected in active explanations; historical ADR-054 preserved
- **Related:** ADR-054/192/193/195; distinct from FINDING-128's Pearson slack policy

## Evidence

At revision `2547c6ef`, the `probabilistic_sharpe_ratio` docstring and validation
cold memory say Normal raw kurtosis 3 reduces the standard-error denominator to
`1/sqrt(n-1)`. Substitute Normal skew 0 and raw kurtosis 3 into the existing formula:

```text
SE^2 = (1 - skew*SR + (kurtosis-1)*SR^2/4)/(n-1)
     = (1 + SR^2/2)/(n-1)
```

The stated simplification holds only at observed Sharpe zero. At per-period
observed Sharpe 1, benchmark 0 and n=2, the current function correctly reports
0.7928919108787373; the incorrect simplification would give 0.8413447460685429.
This is a synthetic formula illustration, not a claim of reliable inference
from two observations. The retained test
`test_psr_reduces_to_lo_s_normal_standard_error_on_a_normal_series` already
asserts the complete correct Normal formula. Independent research review
confirms the algebra and numerical distinction.

ADR-054's immutable Consequences paragraph also describes the Normal case as
the familiar sqrt(n-1) form. Read that historical wording with the complete
Sharpe-dependent denominator above. FINDING-128/ADR-193 address a separate
misidentification of Pearson moment slack as estimator variance.

## Correction and limits

Correct only the active PSR docstring and validation cold-memory explanation:
Normal returns give `sqrt((1+SR^2/2)/(n-1))`, reducing to `1/sqrt(n-1)` at observed
SR=0. This is a documentation correction to the existing estimator, requiring
no new architecture decision. Preserve every runtime expression, domain guard,
assertion, test and historical ADR. No runtime TDD change is claimed.

This finding identifies no numerical defect, affected experiment, incorrect
graduate or invalid historical calibration. It authorizes no estimator,
threshold, gate, fingerprint, accounting-v14, generated-record or frozen-cohort
change. Existing Gaussian-tail saturation and strict moment-domain policies
retain their independently documented limits.

## Verification

Before editing explanations, five complete Normal PSR claims, the whole module
AST outside this sole docstring and the original test-file SHA256 were frozen.
Post-edit replay matches exactly, and 200 existing synthetic PSR/accounting
regressions pass. Independent review and foreground full-gate/publication receipts
remain in the session ledger. These checks verify unchanged implementation, not the general validity
of asymptotic inference or arbitrary finite numerical inputs.

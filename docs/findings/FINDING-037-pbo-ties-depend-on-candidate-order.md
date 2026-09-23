# FINDING-037: PBO ties depend on candidate column order

- **Severity:** High
- **Status:** Resolved by ADR-105
- **Found:** 2026-09-22, Codex autonomous session 6
- **Affects:** CSCV PBO and the production graduation gate

## Finding

`probability_of_backtest_overfitting` selects the first maximum in-sample Sharpe with `argmax` and
ranks out-of-sample Sharpes through two ordinal `argsort` calls. Neither operation gives tied
candidates a permutation-invariant statistical treatment. Reordering the columns of one unchanged
performance matrix can therefore change PBO.

A deterministic eight-row, four-candidate matrix reproduces values of 0.167, 0.333, and 0.500
across column permutations. One representation passes the strict `pbo < 0.5` gate while another
mathematically identical candidate set fails. Exact ties are not merely theoretical: parameter
configurations can remain flat or emit identical discrete signals over a CSCV subset.

Candidate order is execution metadata, not evidence about overfitting. A validation statistic that
changes when hypothesis labels are permuted cannot support a deterministic graduation verdict.

## Required correction

Treat tied in-sample maxima symmetrically by averaging their overfit indicators, and assign tied
out-of-sample Sharpes their average one-based rank before computing the CSCV logit. Add both a fixed
cross-threshold regression and a Hypothesis column-permutation invariant. Do not move `pbo_max` or
any other validation threshold. Advance calibration identity; no workflow dispatch or generated
data edit is authorized by this finding.

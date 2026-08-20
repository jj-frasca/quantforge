# FINDING-002: DSR and MinTRL do not price the search that selects the finalist

- **Severity:** Critical (methodology; the multiple-testing denominator is understated)
- **Status:** Fixed by ADR-046
- **Affected:** ADR-014 through ADR-016, longitudinal and cross-sectional search, null/power
  calibration

## Finding

QuantForge evaluates many concrete parameter configurations inside each strategy family, reduces
each family to one finalist, and then selects the overall finalist across families. The graduation
gate does not price that complete selection procedure.

In the longitudinal path, `ValidationEngine` computes DSR with only the current family's grid size.
`run_search` then selects the maximum family-local DSR across families and records one `Trial` per
family, not per evaluated configuration. `lifetime_trials` consequently grows by the number of
family finalists. Prior search effort reaches MinTRL through that counter but never reaches DSR.

The cross-sectional path counts concrete configurations correctly for MinTRL, but still computes
DSR inside each family and selects the maximum family-local DSR across families. Both paths compare
DSRs produced with different dispersions and different trial counts as though they shared one
selection penalty.

## Evidence

- At `n_per_param=3`, the current 34-family catalog resolves to **667 concrete configurations**
  before optional refinement. `run_search` records 34 trials and adds 34 to `lifetime_trials`.
- Individual family grids range from 3 to 81 configurations. Their DSR haircuts are therefore not
  comparable when the code takes the maximum across families.
- A two-family `sma` + `momentum` run evaluates 16 configurations but records and prices only two
  lifetime trials for MinTRL.
- `ValidationEngine.validate` always calls `deflated_sharpe(..., n_trials=len(configs))`; it cannot
  receive prior lifetime effort or the size/dispersion of the complete searched family.
- ADR-014/015 require the pool's lifetime count to feed the DSR penalty, and ADR-016 calls the stored
  trials the full denominator. The implementation satisfies neither contract.

## Impact

The sealed holdout, PBO, MinTRL, benchmark comparison, and ADR-018 universe bar still provide
independent protection; the measured 1% composite null result is evidence that the old pipeline was
conservative as a whole. It does not make the DSR claim correct. DSR can remain positive after
repeated searches because its denominator resets for every family and every run, and MinTRL is
understated by roughly 20x on the current full-catalog coarse search.

Historical pool records do not contain every old configuration, so their exact candidate count
cannot be reconstructed without guessing against a changed catalog. Existing `lifetime_trials`
must be treated as a lower bound; generated `data/*.json` records must not be rewritten locally.

## Required behavior

- Count every evaluated concrete configuration, including refinement, in `lifetime_trials`.
- Apply one common DSR haircut to every family finalist using the complete current search's Sharpe
  dispersion and the cumulative lifetime count.
- Select the overall finalist only after that common repricing; never compare family-local DSRs.
- Record each family finalist's evaluated-config count so new pool records preserve the denominator
  without storing hundreds of redundant candidate objects.
- Change calibration identity when this accounting methodology changes, so old Type-I/power
  artifacts cannot silently describe the repaired procedure.

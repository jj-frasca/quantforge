# FINDING-269: Negative regime horizons read future market prices

- **Status:** Resolved — ADR-318 original nonnegative horizon guard
- **Date:** 2026-10-18
- **Scope:** Public analyze_regimes horizon evidence

## Reproduction and mechanism

The helper declares a trailing market-return regime but passes an unchecked
window to pct_change. At window=-1 this is p_t/p_(t+1)-1. The independent
five-date witness holds strategy returns fixed at [.01,-.02,.03,-.01,.02] and
market prices initially100. Changing only January4's price to200 moves
January3's unchanged strategy return from bull to bear. An observational
Sharpe wrapper records the original timestamps in each group and delegates
to the original metric. This observes actual group membership rather than
confusing later aggregate changes with an earlier label change.

The separate parent seven-row witness uses window=-2 and changes only market
index4 from100 to250. Strategy return at index2 switches bull to bear while
all prices through that row and every strategy return remain unchanged.
A positive2-window control retains all earlier labels. Receipts:
`/tmp/qf-w42-s33-regime-window-review.md` and
`/tmp/qf-w42-s33-regime-parent-probe.json`.

## Impact and correction boundary

This is a direct public-helper methodology defect. Regime metrics are
retrospective descriptive partitions, but their declared trailing labels
still cannot use later prices. The production ValidationEngine supplies the
fixed default20 chosen in ADR-012; no affected production report, calibration,
API exploit or false graduate is established. Regime metrics do not gate
selection or graduation.

ADR-318 validates original nonnegative nonboolean Integral horizons before
alignment using the unchanged ADR-295 count helper, normalizing supported
NumPy integers to Python int. Zero remains the existing degenerate all-bull
horizon on finite positive prices; it is not a trend estimate. Default20 and
all original alignment/labeling/grouping/compounding/Sharpe operations stay.
No clipping/coercion, data rewrite, threshold, schema, search identity or
accounting-v14 change occurs. Source ordering, missing/nonpositive prices,
alignment policy, arbitrary huge pandas horizons and finite arithmetic remain
separate; no executable regime-switching-account claim is introduced.

## Evidence and verification

Twenty valid pre-edit result payloads across four handbuilt market paths and
horizons0/1/2/20/NumPy-int3 are frozen at
`/tmp/qf-w42-s33-regime-baseline.json`, SHA256
`c06022cd1f9ed5d45d842018ea778ca725fc243371eee562d9dbd0b2696f3896`.
Original source SHA256:
`0d2ac4afd9cf7804e6b476e8c021e42d1e1320ca5934b0f4434ac2a997e19edc`.
Independent precode review approved the one-assignment/shared-import scope.
The actual preimplementation run observed26 failures and5 preserved controls
in3.85s (`/tmp/qf-w42-s33-regime-red.log`), before any production diff.
After the guard, all31 new tests and2 original tests passed (parent2.97s,
independent2.87s). Tests include original invalid classes, refusal before data
access and on empty inputs, Python-int normalization before mocked pandas
(including uint64 maximum), zero/default controls, and Hypothesis properties
for negative refusal and prior timestamp-label identity under prefix/future
perturbations. The huge-count spy proves normalization only; it does not claim
pandas can calculate arbitrary huge horizons. Test regex spelling was polished
to a raw literal after GREEN without changing assertions. Ruff and mypy186 pass.

Parent and independent audits preserved every field of all20 valid frozen
payloads and the entire original module AST after removing only the shared
helper import, one window assignment and restoring the original docstring.
Parent receipt `/tmp/qf-w42-s33-regime-parent-audit.json`, SHA256
`f55ed644b04292ba69bcaa67e267343041f09309e5dc89c6eb4dbb42d748fffe`.
Independent receipt `/tmp/qf-w42-s33-regime-final-audit.json`, SHA256
`615ebd5d0efafa934fa585b2e6d4fa9ca242e4080dfc38ec38c8d4daf7f8a6f8`.
Final source SHA256:
`66921e3071107c8ef6706fadb7dbcf1ccf57bc63c9eb972a7d2ceff6ec78adb1`.
Original tests, count helper, frontend and generated data retain their bytes.
Independent final five-path research review approved. Fresh foreground
`make check-all PYTEST_WORKERS=4` passed12957 backend tests (97.39% coverage)
and438 frontend tests (97.69% statement coverage), with lint, formatting and
strict typing green. Log `/tmp/qf-w42-s33-check318.log`. All verification closed;
production source remained frozen after focused GREEN.

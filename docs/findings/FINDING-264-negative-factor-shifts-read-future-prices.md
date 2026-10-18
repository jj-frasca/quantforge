# FINDING-264: Negative factor shifts read future prices

- **Date:** 2026-10-18
- **Severity:** High for malformed direct configurations — forward causality fails
- **Status:** Resolved by ADR-314 shift-count guards
- **Reviewed source:** e655ef27, cross_sectional/strategies.py and forward.py

## Evidence

momentum_signal accepts lookback=-2 or skip=-3. Its pandas shifts then read
prices after the signal date. Reversal lookback, residual momentum skip and
Alpha19 change_lag also accept negative shifts. Shifting the resulting portfolio
weights by one bar does not restore causality.

An independent deterministic public score_forward witness constructs an accepted
xs_momentum CrossSectionalPosition with lookback=-2, skip=0 on nine dates and four
names. Perturbing only price rows at positions >=6 changes the row5 portfolio
return from 0.0004251700680271142 to -0.02171245161899371, and earlier forward
equity from 0.9494374088013547 to 0.9284280551781142. An independent skip=-3,
lookback=2 witness also changes earlier realized returns. These are synthetic
hand-built direct-call witnesses, with no search, random draw, vendor or cohort.
No actual production occurrence, false graduate or historical contamination is
established. Shipped grids have nonnegative shift counts.

A separate bounded audit of all 16 registry families / 45 configurations across
three fixed six-name, 480-row panels passed 2,700 exact comparisons: signal and
net-return prefixes match truncated and future-perturbed reruns at cuts 1,63,
249,333,479. Fixed ordered universes include ties, flats, oscillations and regime
changes; static score maps are held fixed. Receipt /tmp/qf-w42-s31-xs-audit.json
and executable /tmp/qf-w42-s31-xs-audit.py. Initial receipt generation failed only
at a relative source-hash path after comparisons; corrected complete rerun passed.
This is bounded negative evidence, not a universal causality, point-in-time
fundamentals, calibration or pipeline-power proof.

## Governed correction

ADR-314 validates five shift-producing counts at the direct signal boundary,
normalizes original nonboolean Integral scalars before addition and preserves
zero periods. Existing factory int coercion remains an explicit separate limit;
no original factory-type validation is claimed. Rolling-window and arbitrary
custom-signal contracts remain separate. No formula, shipped grid, threshold,
longitudinal calibration identity, frozen attempt or generated record changes.

## Verification

Actual pre-implementation RED: 57 failed, 22 preserved in 6.69s, before any
production edit (/tmp/qf-w42-s31-shifts-red.log). Cases cover five original
count domains before panel access, negative empty panels, six public forward
reconstruction routes, and an intercepted fixed-width period sum. The sum witness
tests normalization only; its enormous native numerator shift is all missing,
so it is not evidence of realized overflow-induced lookahead.

After the five guards and one import, 267 focused cases passed in 8.70s,
including all 79 new cases. Zero/native integer original-formula controls,
Hypothesis exact signal/net-return prefix and future-perturbation invariants,
and all shipped price-grid prefixes passed. Independent six-path review approved
the correction and independently passed all 79 cases. Both parent and independent
AST comparisons restore the entire original source by removing only that import
and those five assignments; all signatures, docstrings and operations match.
Parent exact original/current comparisons passed all 45 registry configurations'
signal and net-return outputs on a fixed panel. Receipts:
/tmp/qf-w42-s31-xs-independent-review.json and
/tmp/qf-w42-s31-xs-parent-baseline.json. Corrected source SHA256:
ef0c1745a301f10cd828b6e9045e797978b8594bb974f503b58169b06bbe40c2.

Fresh foreground make check-all passed 12,866 backend cases (97.39% coverage)
and 438 frontend cases (97.69% statements), including lint, formatting and strict
types. Log /tmp/qf-w42-s31-check314.log; all local verification closed successfully.
Exact master CI is verified after individual publication.

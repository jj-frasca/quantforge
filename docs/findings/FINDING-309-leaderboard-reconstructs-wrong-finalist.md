# FINDING-309: Leaderboard joins an unselected trial to the selected graduate

- **Severity:** High — published strategy and graduation attribution
- **Found:** 2026-10-25, Codex autonomous session32 (ISO2026-W43)
- **Status:** Corrected by ADR-369
- **Affected:** `rank_experiments` in `backend/app/research/lab/universe.py`,
  consumed by `/api/v1/leaderboard`, `/api/v1/graduates` and pool summary ranking

## Evidence

ADR-079 persists the exact trial sent to holdout and graduation, including
same-family refinement identity. The canonical Experiment boundary checks that
its graduate matches that selected trial. However, rank_experiments independently
chooses the maximum deflated_sharpe inside each experiment and joins that trial's
strategy and margin to the experiment's graduate and holdout evidence.

A constructed, fully validated Experiment survives JSON roundtrip with selected
momentum margin0.2, an unselected sma margin0.8, and a momentum graduate carrying
holdout Sharpe2 over252 bars. Its leaderboard row says sma, margin0.8,
graduated=True and holdout Sharpe2. No unchecked model copy is required.
Independent review also reproduced the defect with an actual default
GraduationGate evaluation: momentum observed3/margin1.6/WF0.2 versus selected
sma observed2/margin0.6/WF0.9, two evaluations each, lifetime4, available100years,
holdout Sharpe2 over1008bars and benchmark0.3. The selected sma passes, but the
row attributes graduation to momentum. With both trials named sma, the margin
still comes from the wrong configuration. These synthetic records establish
projection behavior, not an affected committed experiment or false graduate.

## Scope and correction

Resolve each nonempty experiment through existing selected_trial, preserving its
legacy max-margin fallback. Keep the existing cross-experiment policy: one row
per symbol, graduates first, then the represented finalist's margin. Unique
symbol count, holdout/universe annotation, value score, empty-trial behavior and
public fields remain unchanged. A name-only selection cannot distinguish two
refinement trials. Search, gate predicates, thresholds, v14 identity, generated
records and all frozen cohorts require no change. The defect misreports an
existing verdict; it does not demonstrate a gate error or change graduation.

## Verification

The new regression module observed ten failures and three passing controls
before the source change, then all13 passed. It covers cross-family and
same-family identity, graduated and nongraduated records, JSON reload, scratch
store plus both HTTP projections, repeated-symbol representative selection,
its pool survivor-count consequence, legacy payloads, empty trials and a
Hypothesis selected-identity property. The focused existing/new suite passed
61tests; independent final research review approved all six paths and reran
all13 new tests successfully.

A baseline captured before the patch and replayed afterward preserves32
ordinary/legacy row payloads and the entire prior module AST except exactly
the selected assignment and leading function docstring. A fresh read-only
compatibility comparison preserves all607 current leaderboard row payloads
from3300 validated experiments and all607 source partition hashes. This does
not reconstruct past observations or certify other report statistics. No
generated record was written. Receipts: `/tmp/qf-w43-s32-leaderboard-red.log`,
`-focused.log`, and `/tmp/qf-w43-s32-leaderboard-preservation.log`.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed:14759 backend tests,
746 frontend tests,97.42% backend coverage and97.88% frontend statements;
lint, formatting and strict typing passed. Full receipt:
`/tmp/qf-w43-s32-check369.log`. Thresholds, scientific algorithms, accounting-v14,
generated records and frozen sources remain unchanged.

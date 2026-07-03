# ADR-018: Universe-level deflation for cross-symbol selection

- **Status**: Accepted
- **Date**: 2026-07-02
- **Deciders**: Joe Frasca
- **Extends**: ADR-015 (statistical-power policy), ADR-016 (gate)

## Context
The per-symbol graduation gate (ADR-016) deflates for the trials on *each* symbol, but a universe
hunt selects the best few of N symbols — a **second** multiple-comparisons layer it doesn't price
in. The 2026-07-02 hunt surfaced 2 graduates out of 51 names; picking the best 2 of 51 is itself
a selection that inflates the apparent edge. Trusting a universe "winner" without accounting for
this is exactly the overfitting the project exists to defeat.

## Decision
Add a **universe-level deflation** annotation: a graduate is only distinguishable from lucky
cross-symbol selection if its holdout Sharpe exceeds the **expected maximum Sharpe under the null**
(no skill) across N symbols.

`expected_max_sharpe_under_null(n_symbols, holdout_years) ≈ SE · √(2·ln N)`, where the annualized
Sharpe standard error `SE ≈ √(1 / holdout_years)` (Lo 2002, dropping the higher-Sharpe term for a
conservative-but-simple bar). A graduate `survives_universe_deflation` iff its holdout Sharpe
exceeds that threshold.

Applied as a **leaderboard annotation, not a retroactive veto** of the per-symbol Experiment
record: the per-symbol graduate is still a real, reproducible fact; the universe flag is the
additional cross-symbol scrutiny. The hunt reports "X passed the per-symbol gate; Y survive
universe-level deflation." Expected effect: with a 51-name universe and ~4y holdout, the null
expected-max Sharpe is ~1.4 — so most/all current graduates will NOT survive, which honestly says
"these are indistinguishable from selection luck; forward-testing on truly new data is the only
way to know" (motivating ADR-019 paper trading).

## Options Considered
- **Hard universe veto** (strip graduate status). Rejected: conflates the per-symbol result (a
  reproducible fact) with the cross-symbol caveat; annotation is more honest and preserves the record.
- **Inflate per-symbol MinTRL by the universe trial total.** Rejected: double-counts the per-symbol
  DSR deflation and muddies the two distinct selection layers; a separate explicit test is clearer.
- **Full Deflated-Sharpe with cross-symbol trial count + skew/kurtosis.** Deferred: the expected-max
  approximation captures the first-order effect; the fuller treatment can supersede this later.

## Consequences
- The leaderboard now tells the honest cross-symbol story; a "universe survivor" is a much stronger
  claim than a per-symbol graduate.
- Likely shows 0 current survivors — which correctly routes us to forward-testing (ADR-019) rather
  than trusting in-sample-selected names.
- New obligation: the Graduate record carries `holdout_n_bars` so holdout length is known downstream.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*

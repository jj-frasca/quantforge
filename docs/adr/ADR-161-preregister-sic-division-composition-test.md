# ADR-161: Pre-register the SIC-division composition test for the 7,400-vs-9,247-bar excess gap

- **Status**: Accepted (test not yet run — see "Run gate")
- **Date**: 2026-10-04
- **Deciders**: Autonomous session #151 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-146 (captured the raw `sic_code`; deferred the test to "its own ADR")
- **Relates to**: ADR-094 (named sector mix as an unmeasured composition candidate), ADR-095
  (`sic_description`), ADR-063/070/074/076 (state estimator and threshold before seeing the answer)

## Context

ADR-146 waited for `sic_code` to build coverage. The 2026-10-04 `fundamental-sweep` has landed
(`37199689275`); `origin/master:data/fundamentals_pool.json` carries `sic_code` on 3,414 of 4,246
rows. Before writing any criterion this ADR measured only what the meta-lesson says to measure
first — whether the sample exists and how big the statistic's standard error is — and **did not
tabulate division x cohort or division x excess**. Facts used (from `pool_report`'s own matching,
`HISTORY_TOLERANCE` = 10%, per-symbol mean of the finalist's walk-forward OOS Sharpe minus
`walk_forward_hold_sharpe`):

| cohort | matched symbols | with `sic_code` today | in pool, desc but no code | absent from fundamentals pool |
|---|---|---|---|---|
| 7,400 bars | 92 | 54 | 8 | 30 |
| 9,247 bars | 276 | 189 | 41 | 46 |

Per-symbol excess SD is ~0.23 / ~0.22, so the SE of each cohort mean is ~0.03 / ~0.015 and the SE of
the raw cohort gap is ~0.033 against a gap of ~0.08 — the gap itself is detectable at roughly 2.4 SE,
and anything that *adjusts* it (post-stratification inflates variance) is weaker still. **This test
is power-limited by construction; "inconclusive" is the most likely honest outcome and is a
legitimate result, not a failure.**

The 8 + 41 "desc but no code" rows predate ADR-146 and fill on the next sweep. The 30 + 46 "absent"
symbols are **not** a lag: the fundamentals pool excludes ETFs, ADRs/foreign filers and (visibly)
many financials (`GS`, `BAC`, `COF`, `MET`, ...). That is a selection effect on exactly the sector
(finance/REITs, SIC Division H) ADR-146's first look flagged, so the test can only speak to
fundamentals-eligible symbols, never to the whole cohort.

## Decision

**Run one single-look test, exactly as specified below, once the run gate is met. Nothing here is
tunable after the data is seen.**

1. **Division scheme (external, fixed).** SEC SIC divisions by 2-digit major group: A 01-09,
   B 10-14, C 15-17, D 20-39, E 40-49, F 50-51, G 52-59, H 60-67, I 70-89, J 91-99. A symbol's
   division is `int(sic_code[:2])`'s range. Symbols with null/unparseable `sic_code` are dropped
   (complete-case) and their counts per cohort reported.
2. **Collapse rule (stated now, applied mechanically).** Any division with fewer than 5 symbols in
   the two cohorts combined is merged into `Other`. No other regrouping, ever.
3. **Per-symbol statistic.** Mean over the symbol's matched experiments of
   `selected_trial(e).walk_forward_oos_sharpe - e.walk_forward_hold_sharpe` — the same
   symbol-clustered construction `_excess_rows` uses. Cohorts = `pool_report._matched` at 7,400 and
   9,247 bars. **Estimator: the mean** of per-symbol values (not the median; ADR-074's own lesson).
4. **S1 — composition differs?** Chi-square statistic on the division x cohort table, p-value by a
   10,000-draw label permutation (seed `20261004`). Reject at p < 0.05.
5. **S2 — does composition close the gap?** Raw gap = mean(7,400) - mean(9,247). Adjusted gap =
   mean(7,400) - the 9,247 cohort's post-stratified mean using the 7,400 cohort's division weights
   over divisions present in both (weights renormalised). 95% percentile intervals for both from a
   10,000-draw symbol bootstrap resampled within cohort x division (seed `20261004`).
6. **Pre-stated readings** (evaluated top to bottom, first match wins):
   - **Composition explains the gap**: raw-gap CI excludes 0, S1 rejects, adjusted-gap CI includes 0,
     and |adjusted| <= 0.5 x |raw|.
   - **Composition does not explain the gap**: raw-gap CI excludes 0, adjusted-gap CI excludes 0
     with the raw gap's sign, and |adjusted| >= 0.5 x |raw|.
   - **Otherwise: inconclusive** (including the case where the raw gap's CI includes 0 — then there
     is nothing to explain). Report intervals as measured; make no directional claim.
7. **Run gate.** Run only when, in BOTH cohorts, rows present in the fundamentals pool but missing
   `sic_code` are <= 5% of that cohort's matched symbols (the sweep has refreshed them). Until then
   do nothing — do not run it "early to peek". Report the absent-from-pool counts alongside the
   result and state that the conclusion is restricted to fundamentals-eligible symbols.
8. **Single look.** No sequential design. A follow-up needs its own ADR that sizes and pre-registers
   a fresh sample or an explicit two-look boundary (ADR-076 pattern). This test touches no gate,
   threshold or search path; it is read-only analysis.
9. **Implementation slice (later commit, TDD):** `backend/scripts/sic_composition_test.py` reading
   `data/research_pool/`, `data/fundamentals_pool.json`; pure functions for division mapping,
   collapse, S1, S2 with Hypothesis properties (division map total over 01-99; post-stratified mean
   of a cohort against its own weights equals its mean). Output to
   `data/sic_composition/result.json` (<500 KB), never to the pool (ADR-030).

## Alternatives considered

- **Bucket the free-text `sic_description`.** Rejected: ADR-146 saw those labels before any scheme
  existed; any grouping would be fit to the look.
- **Regress excess on division dummies pooled across cohorts.** Rejected: ~10 parameters on 54
  symbols in one cohort; the post-stratification contrast answers the actual question with fewer
  degrees of freedom.
- **Median instead of mean.** Rejected: the question is about mean shift of a stable statistic; the
  mean has the tighter interval at this n (ADR-074).
- **Backfill `sic_code` locally to hit the gate sooner.** Rejected: would make this session a second
  writer of a cloud-owned file (ADR-030).

## Consequences

- Adds only this document; no code, data or threshold changes. The run gate may take one or two
  more weekly sweeps; it is not expected ever to be satisfied for the ADR-absent symbols.
- **Reverse**: set Status to Superseded; nothing depends on it.

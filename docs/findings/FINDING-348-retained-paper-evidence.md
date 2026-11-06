# FINDING-348: Open paper configurations conceal a negative retained-history comparison

- Date: 2026-11-05, ISO 2026-W45 session 1
- Status: reproduced retrospective negative comparison under ADR-413; no positive alpha claim
- Independent research-expert review: approved scope before implementation

## Question and evidence boundary

Does the surviving paper-config book tell the same economic story as all retained
positions? ADR-020 retains closed positions, while the existing pool report's
headline summarizes open positions. This is intentional open-book reporting, not
an arithmetic defect. Interpreting it as the strategy program's full record loses
the failures that lifecycle closed.

The current scorecard at `4c73eb22` reports 3,309 experiments / 607 symbols /
6,507,982 recorded lifetime trials, 274 graduate experiments, 41 distinct graduate
symbols and zero universe-deflation survivors. The independent reviewer inspected
the paper snapshot during task selection and found an open/all sign reversal.
These signs were known before ADR-413; no untouched confirmatory sample exists.
ADR-413 fixes the reporting hypothesis, comparison, selection accounting, geometry,
cost limitations and acceptance criteria before implementation. No new strategy
experiment or selection decision is made here.

## Result

Full source revision: `4c73eb228a2b4294da18d5d778bc89b8de975c14`.
Paper input SHA256:
`5e90de13895fa49055e8f87249917a40cc57f9cdf1dd2beab9a5f81b1bf53897`;
Git blob: `077e488bf365e3bd5ef1c5f2b48d4ef27072f49e`.

| Recorded population | All | Open | Closed |
|---|---:|---:|---:|
| Positive-bar scores / positions | 44/44 | 7/7 | 37/37 |
| Forward-bar range | 21–86 | 47–76 | 21–86 |
| Median paired terminal return difference (percentage points) | −1.8273 | +7.3855 | −1.9123 |
| Mean paired terminal return difference (percentage points) | −3.6551 | +5.3870 | −5.3657 |
| Median paired Sharpe difference | −1.1226 | +0.6384 | −1.5675 |
| Positive terminal return differences | 14 | 5 | 9 |
| Positive Sharpe differences | 10 | 4 | 6 |
| Stored Sharpe-beat flags | 8 | 2 | 6 |
| Zero recorded forward-turnover events | 33 | 5 | 28 |
| Affirmative nonzero strategy-curve evidence | 21 | 2 | 19 |
| Dataset lineage present | 12 | 7 | 5 |
| Recorded full curves | 44 | 7 | 37 |

Every retained position has a score and curve; there are no missing or zero-bar
scores in this snapshot. Five of seven open configurations have an exactly unit
strategy curve with zero recorded turnover; their relative return can be positive
because the same-name holding control lost money. All-zero returns alone do not
prove flat exposure. Stored historical flags are preserved, which is why positive
Sharpe differences and stored beat counts differ. These are not new policy verdicts.

Deflation membership is 0 survivors, 1 non-survivor, 43 unknown. No position has
126 forward bars, so ADR-033's comparison is unavailable. Unknown is not failure
or success. Repeated symbols and a shared calendar preclude treating the 44 rows
as independent draws; the earlier 6,507,982 count is the recorded search denominator,
not an additional denominator inferred from this book.

Independent raw-JSON arithmetic reproduced the source hash/blob, counts and all
paired means/medians without calling the new reporting helper. The report writes
stdout only and revalidates position claims. It neither fetches new data nor runs
search. All old frozen sources, cohorts and timing roots remain untouched. No
generated record is edited and no gate or validation threshold moves.

Reproduce the exact historical input after later cloud updates, from repo root:

```sh
git show 4c73eb228a2b4294da18d5d778bc89b8de975c14:data/paper_portfolio.json > /tmp/qf-f348-paper.json
cd backend
UV_OFFLINE=1 PYTHONPATH=. uv run python scripts/paper_evidence_report.py /tmp/qf-f348-paper.json
```

The emitted SHA256 must equal the value above. With no positional argument the
command instead describes the current committed working snapshot, a new
descriptive look, not a refresh of this finding's frozen measurement.

## Interpretation and next experiment

**The positive alpha case did not improve.** This evaluation improves honesty;
the surviving subset's positive median reverses when closed configurations are
retained. This is a survival/stopping diagnostic, not proof that any particular
exit policy caused underperformance. Paired same-name controls
match each record's own horizon; horizons differ and lifecycle stopping is
outcome-dependent. Neither all-position means nor survivor means are an account
return or an unbiased common-horizon estimate. Costs are internal modeled turnover
costs under current producer code, with no durable historical rate attestation.

The next concrete experiment is a separately reviewed **63-session common-horizon
forward comparison**: freeze the complete eligible configuration list before its
future start, compare an explicitly funded equal-weight policy with same-name
holding and cash, charge declared entry/exit/turnover costs, and retain exits as
cash through the fixed endpoint rather than dropping losers. Fix selection/trial
accounting, shared-calendar inference and a net-benchmark acceptance rule in a new
ADR before exposing that future window. This is a proposal, not an adopted cohort
or permission to synthesize missing historical account costs. First build and test
the required position/capital/entry/exit accounting; current score-only evidence
cannot execute this comparison honestly. Existing recorded paths must remain intact;
never extend or retry an expired or incomplete historical calibration cohort.
ADR-033's existing 20-per-known-cohort / 126-bar trigger remains unchanged.

## Verification

Actual pre-implementation RED: seven collected tests failed because the reporting
module did not yet exist; the same seven then passed. Added coverage exercises
first-bar/round-trip path evidence, legacy missing lineage, input-byte preservation,
claim revalidation, maturity boundaries and paired-difference Hypothesis invariants.
The CLI test initially omitted its Python import context and the synthetic lineage
fixture initially omitted required checked_at; both fixture errors were corrected
without source or expectation weakening. Final focused suite: 12 passed (parent 22.72s; independent 20.05s).
Independent final six-path research/code review approved; full-gate receipts follow
in the session ledger; no experiment outcomes were changed in response to tests.

Final foreground `make check-all` completed successfully: 17,784 backend tests
(97.51% coverage), 781 frontend tests (97.89% statement coverage), lint, formatting
and strict types. FINDING-349 documents the separately reviewed incidental timing
settings needed for two existing properties; all original scientific assertions
and thresholds remain intact.

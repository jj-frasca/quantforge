# ADR-413: Report retained paper evidence before judging alpha

- **Status:** Accepted
- **Date:** 2026-11-05 (local), ISO 2026-W45 session 1
- **Deciders:** Codex autonomous peer; independent research-expert review approved
- **Extends:** ADR-019, ADR-020, ADR-033, ADR-361, ADR-366

## Context and economic hypothesis

The mission is credible after-cost out-of-sample alpha. The current pool headline
and paper account do not establish it. An open-only configuration scorecard can
conceal unsuccessful closed configurations and mistake avoiding a falling stock
for evidence of a profitable signal. The economic question for this bounded
production evaluation is whether the retained frozen-config record supports the
optimistic reading of the surviving book.

This is **retrospective descriptive evaluation**, not a new confirmatory experiment.
The independent reviewer inspected the current snapshot and reported the direction
of the open/all comparison during task selection, before this decision. There is
no untouched test sample here and no alpha acceptance test is being invented.

## Fixed comparison and accounting, before implementation

Input: every record in `data/paper_portfolio.json` at revision
`4c73eb22` (full revision resolved in the finding), Git blob
`077e488bf365e3bd5ef1c5f2b48d4ef27072f49e`, SHA256
`5e90de13895fa49055e8f87249917a40cc57f9cdf1dd2beab9a5f81b1bf53897`.
One snapshot look, zero searches, zero fitted parameters, zero new strategy trials.
Repeated deterministic renders and synthetic tests validate reporting only.
Existing lifetime search counts remain the authoritative selection accounting;
44 retained positions are not 44 independent bets. No symbol/family is selected
from the result, and no existing source, cohort or timing root is revisited.

Report all/open/closed populations without further screening. Present absent and
zero-bar scores separately. Include every positive-bar score, including zeros and
zero turnover, in paired summaries. For each such score report strategy minus
same-name buy-and-hold terminal simple return and Sharpe; summarize their median
and mean and count positive return differences. Report the stored Sharpe-beat
flag separately from positive Sharpe differences (inactive rows can differ).
Keep complete row identity, horizon, freeze/as-of dates and status visible.
Count curve availability, quality-lineage availability, zero-turnover records,
and affirmative nonzero strategy-curve evidence; legacy missing curves mean
unknown path evidence, not zero. Count deflation true/false/unknown and >=126-bar
observations in each, keeping ADR-033's >=20 per known cohort unchanged.

Evaluation geometry stays exactly as recorded: strictly after each original
freeze, ending at its existing score cutoff. Closed paths stop at lifecycle exits;
they do not acquire hypothetical later performance. Different horizons and
outcome-dependent stopping preclude an unbiased common-horizon pooled estimator.
No concatenated portfolio return, inferential interval, p-value, or annualized
terminal-return comparison is produced.

Costs: current `evaluate_forward` uses the warmed full-frame engine and its
10bp per unit turnover default. Its same-name holding control is gross.
ForwardScore stores no historical cost rate; the report cannot attest the rate
actually used for a legacy row, recover entry/switch charges, financing, borrow,
slippage or broker execution. Never call these differences account alpha.
The separate broker ledger is outside this report's input and attribution.

## Acceptance criteria and decision

Success means reproducible complete-denominator reporting, preservation of all
recorded identities/values, explicit missingness/cost/horizon limitations and an
honest written finding. A positive descriptive median is insufficient to improve
the alpha case. No strategy, allocation, lifecycle, gate, threshold or producer
changes on this evidence. The ADR-033 cohort comparison remains unavailable until
its original maturity/sample requirements hold.

Independent research review approved this scope before implementation with the
retrospective, inactivity, stopping, stored-flag and historical-cost caveats above.
Use synthetic TDD including a survivor-sign reversal, missing/zero-bar evidence,
inherited zero-turnover returns, immutability and financial difference invariants.
Run full foreground gates, then independently reproduce the snapshot result.

## Alternatives and reversal

Another indicator or an in-sample search would not resolve the demonstrated
evaluation ambiguity. A common-horizon prospective experiment needs its own
independent review and genuinely untouched future window; it is not authorized
by this retrospective result. An executable account reconstruction requires
holdings and execution evidence absent here.

The new standalone read-only report is reversible by ceasing to use it. Existing
producers, public API, generated records, historical evidence and frozen experiments
are unchanged.

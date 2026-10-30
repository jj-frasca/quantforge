# FINDING-344: Nonzero DCF per-share division becomes zero value

- **Status:** Corrected within final-division zero loss (ADR-409); earlier precision remains open
- **Date:** 2026-10-30, Codex autonomous session22 (ISO2026-W44)
- **Severity:** Confirmed finite-input evidence loss; production incidence unmeasured
- **Affected:** dcf_intrinsic_value, composite valuation and record/provider consumers
- **Related:** ADR-022/373/395/407/408/409; distinct from source-period/PIT questions

## Actual producer witness

At revision 218faebd, two ordinary AnnualFundamentals rows with constant FCF
1e-300, shares1e300, revenue1e308, net income1, EPS1 and history price10 produce
finite native equity_value1.2276711517883563e-299 under default assumptions.
The final division by shares rounds to0.0. Fraction(native_equity)/Fraction(shares)
is strictly positive and below half the least positive binary64 subnormal.
No earlier projection/accumulation zero is needed for this witness.

At current price1, score_valuation returns intrinsic value0, absent margin of
safety, both own-history percentiles0, composite1 and no flags. The default value
screen passes; the optional positive-margin requirement still rejects absence.
Actual injected value-provider and fundamental-record consumers retain the value
score1. These extreme synthetic accepted inputs establish a code path, not realistic
corporate scale, internally reconciled accounting, vendor incidence, a historical
record, false graduate or trading effect. No acquisition or search is needed.

Independent research/data reproduce the witness and exact accepted-float oracle.
Custom finite growth bounds of -2 also yield a nonzero negative equity numerator
and signed-zero quotient; a true-zero-equity control remains zero. Nonzero
subnormal quotients remain measurable under the existing native precision policy.

## Correction and limits

ADR-409 computes the existing final quotient once, then raises plain ValueError
when equity_value !=0.0 and that quotient ==0.0. It recognizes definite loss of
nonzero native numerator evidence, including either signed zero; no tolerance,
precision recovery, None fallback or new economic input policy is introduced.
Genuine zero equity and all nonzero quotients retain existing behavior, including
nonzero subnormals and the existing direct/nonfinite-output contracts.
Earlier projection, discounting, terminal and accumulation underflow/cancellation,
ordinary rounding, complete exact-real DCF correctness and source/PIT truth remain
outside this correction. It does not certify zero accumulators or nonzero results.

Refusal propagates through composite scoring, records and injected value providers.
The existing universe boundary records a per-symbol error before downstream frame
acquisition/search, even with the optional value screen off. Sweep scoring remains
outside acquisition recovery and can fail a shard before output; no new catch,
partial output or unscored substitution is added. Availability can decrease.
No threshold, fingerprint, v14, generated record, frozen cohort or historical repair.

## Verification

Before implementation, freeze 1,140 complete ordinary direct/composite/record
outcomes, whole module AST and six original test hashes in
/tmp/qf-w44-s22-dcf-zero-baseline.{py,json}. Baseline includes true zeros, nonzero
subnormals, early returns, custom settings, nonpositive horizons and existing
native errors. It is bounded compatibility evidence, not a universal proof.
Actual pre-code RED, final independent reviews, foreground full gates and exact
publication/CI receipts are recorded below or in CODEX_RUNNING_STATE as completed;
no uncompleted verification is claimed here.


Actual initial pre-code run: 29 failures and 6 controls. Two failures were incorrect
new control expectations for singleton histories: historical percentiles are
unavailable, so genuine-zero DCF leaves composite None rather than 1. Both tests
were corrected before any production edit, retaining both cases. A failed-cwd
correction attempt left the tests unchanged and repeated that original result;
it is not corrected RED. The corrected actual pre-code run then produced
27 expected failures and 8 controls (35 cases), with production diff empty.

After the narrow source patch, all 35 new cases and 277 focused synthetic tests
pass. Financial Hypothesis tests bound positive perpetuity values below half the
minimum positive float; direct/composite tests cover both quotient signs and
proxy/FCF with singleton/multirow histories. Record/provider and universe tests
verify refusal before downstream acquisition with the value screen off/on.
True-zero and both-sign nonzero subnormal controls pass. No old test was changed,
deleted or skipped. Parent and both final independent reviews reproduce all 1,140
complete baseline outcomes, scoped whole AST and six old test hashes exactly.
Both reviewers independently run the 35 new cases and approve all six paths.
Foreground full-gate and exact publication/CI receipts remain in the session
ledger; these focused checks do not claim those unfinished checks passed.

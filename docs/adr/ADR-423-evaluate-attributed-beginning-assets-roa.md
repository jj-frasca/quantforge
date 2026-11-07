# ADR-423: Evaluate attributed beginning-assets ROA through quality scoring

- **Status:** Accepted
- **Date:** 2026-11-07
- **Deciders:** Codex W45 session9 under standing autonomy
- **Extends:** ADR017/022/029/117/155/389/390/395/397/399/419; FINDING324

## Problem, hypothesis and review

The quality/value portfolio needs usable, correctly attributed inputs. F324
already demonstrates that same-year closing Assets reverse the improving-ROA
point relative to beginning Assets on one retained Apple observation. A funded
account cannot repair that score-component mismatch. Full portfolio evaluation
also remains blocked by truthful history and untouched geometry. This task
addresses the demonstrated component, not the entire backtest.

Independent research and data design reviews approved the contract before this
adoption or implementation. Research helped draft the proposal; its conformance
review is independent of the implementing agent, not draft-naive. Final actual
source/default-preservation review must be performed by nonimplementers.

Hypothesis: actual beginning denominators in the existing scorer reverse the
known FY2022 trend point while preserving other witness components and all
legacy default claims. Deliver ONE network-free source-to-scorer-to-quality-to-
no-price-record evaluator, with retained evidence. No isolated ratio helper,
post-hoc boolean override or subtraction is success. This is a known-witness
method comparison, not blind OOS or a new economic experiment.

## Fixed evidence and comparison before implementation

Use only the existing full Apple CompanyFacts capture:
`docs/evidence/FINDING-322/companyfacts.CIK0000320193.20261030.json.gz`.
Decoded SHA256:
`73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43`.
CIK320193/symbolAAPL; original URL
https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json .
Inherited completion claim2026-10-30T07:28:44.145492+00:00 comes from F322's
retained transport receipt, not first public availability. Verify actual bytes
before selection, issuer identity and aware as_of>=observation, normalized UTC.
No filed date becomes a historical observation; no new HTTP, prices or sources.

Compare default and opt-in on the identical unchanged parser history prefix
ending FY2022. Preserve ALL supplied fields and its original2025 accession
0000320193-25-000079. Retain complete canonical history SHA and full history
beside results. Never relabel that envelope as a contemporary2022 artifact.
Unrelated fields and earlier rows remain unverified legacy inputs.

Fix explicit caller assertions, NOT audited original DEI anchors:

- FY2021 accession0000320193-21-000105, 2020-09-27 through2021-09-25.
- FY2022 accession0000320193-22-000108, 2021-09-26 through2022-09-24.
- Earliest closing Assets: FY2020 accession0000320193-20-000096,
  instant2020-09-26.

These known F324 intervals are364 inclusive days; impose no365-day guess.
Require start<end, consecutive labels and prior_end+1day==latest_start.
Annual.period_end derives from revenue and is NOT ROA period evidence. Preserve
it unchanged; source groups below carry the independent income/Assets dates.

## Source and history contract

Interpret only literal us-gaap:NetIncomeLoss/USD and us-gaap:Assets/USD, without
tag fallback, longest-duration or latest-row inference. Require two exact
income duration groups and five Assets groups at three physical dates: original
2020closing; its comparative in2021filing; original2021closing; its comparative
in2022filing;2022closing. Assets require ABSENT start; explicitnull is unsupported.
Income requires exact start/end. Original closing accession is explicit even
for the earliest balance, never selected for a desired value.

Select physical period/accession first. Matching rows with contradictory
required metadata refuse rather than disappear. Require10-K, reported FY,
FY-focus and consistent valid filed labels within each same-filing group.
Retain every original-present row key, namespace/tag/unit, agreeing duplicates
and absence/null distinctions in canonical order. Every required group must
exist; all exact numeric values agree before float projection. Refuse conflicts,
booleans, strings, nonfinite values, nonpositive Assets or unrepresentable values.
Comparative and prior original closing values must agree exactly before
projection. This is aggregate byte-to-row linkage, not original XBRL audit.
NetIncomeLoss remains a conditional proxy for the paper's different numerator.

Reconstruct the supplied history. Last three labels and Assets projections and
last two income projections must match these groups. Bind the COMPLETE history
JSON hash, symbol and CIK; do not replace numeric fields or attach evidence to a
different history. Retain its complete original envelope and graph. This does
not establish annual alignment or PIT for unrelated history fields.

## Integrated opt-in and retained identity

Add immutable typed ROA evidence carrying method identity, issuer/symbol,
intervals, source observation, all source groups, actual scalar projections and
history SHA. The outer evaluator verifies bytes and constructs evidence. A
scorer's supplied model is an attributed claim, not authentication merely from
a hash string. Scorers revalidate evidence and bind it to actual history.

Pass optional keyword roa_evidence=None through piotroski_f_score, quality_score
and compute_fundamental_record. Present malformed evidence refuses, never falls
back. Validate explicit evidence before a short-history shortcut. DefaultNone
preserves existing formulas, early returns, errors, flags and serialized shapes.
FScore schema stays; QualityScore and FundamentalRecord retain optional evidence
omitted whenNone. Record validation binds available symbol/CIK/latestFY; it does
not pretend to recompute absent full history. Existing whole-winner merges retain
the winner's own evidence, including an unknown legacy winner.

Explicit mode computes both income/Assets ROAs and latest CFO/Assets with the
actual beginning denominators. Existing finite, underflow and exact-predicate
checks receive those actual denominators. Compute all nine verdicts normally,
then the actual quality blend and record. Strict positive shared denominators
preserve ROA/CFO signs and accrual ordering. The five other components, GP,
safety, leverage, turnover, dilution and income/CFO mappings remain unchanged.
No boolean substitution or mathematical-guard weakening is permitted.

No-price scope is fixed: the evaluator has no price option. Producer with
present evidence and ANY nonNone price refuses BEFORE scoring/valuation. Direct
record construction with present evidence and nonNone value/combined refuses.
Evidence-absent priced behavior stays unchanged. The outer result retains full
history, observation, assertions, evidence, actual default and opt-in FScore,
QualityScore and Record, exact ratio comparison and evaluated cutoff.

## Acceptance, accounting and verification

Known income2021/22:94680000000/99803000000. Assets2020/21/22:
323888000000/351002000000/352755000000. Default closing ROA increases from
47340/175501 to99803/352755; beginning ROA declines from11835/40486
to99803/351002. Actual default F-score8/trendTrue must become opt-in7/trendFalse,
with the other eight witness verdicts unchanged. Default quality is
0.6675842309900554; opt-in quality must use the unchanged blend and actual new
F-score. GP/safety exact; price/value/combined absent. Preserve original history,
source bytes, all old default claims and frozen cohorts exactly.

TDD actual collected RED before implementation. Cover both reversal directions,
constant positive Assets, Fraction financial properties, source/hash/issuer/
aware-cutoff/history mismatches, missing/conflicting groups, comparative mismatch,
nonpositive balances, physical gaps, malformed metadata, absent third balance,
immutable evidence, omission/roundtrip/whole-winner identity, and no-price
refusals. Capture default claims and protected source/cohort hashes before code.
Obtain independent final source/result and default-preservation reviews,
foreground make check-all, individual fresh-sync publication and exact CI.

Zero new source, price, configuration or economic trials; no new selection,
effective-N reset or pooling. Prior technical/quality-value and ADR414–418 trials
remain recorded. Costs/resources$0; no financed account, return geometry,
turnover, exposure, drawdown or benchmark result. PBO/DSR/WF/holdout/graduation
NOT MEASURED. Correcting this component does NOT improve alpha evidence.
Numerator equivalence, unrelated periods, turnover definition and share/split
basis remain unresolved; no complete Piotroski, all-filer or PIT claim.
ADR417 stays terminal,422 permanently expired,418's February11 final economic
screen and every other frozen cohort/root remain unchanged, with no interim look.

Alternatives: replace default scoring now (would silently reinterpret historical
scores); subtract the known point (not an integrated method); build a full gate
adapter (missing dated inputs and account geometry); acquire another source
cohort (unnecessary and cannot replace expired422). The explicit retained path
is reversible without claiming those broader capabilities. Remove opt-in wiring
to reverse; preserve all historical evidence and default records.

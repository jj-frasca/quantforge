# ADR-302: Require ordered unique source calendars before holdout splitting

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 23, ISO 2026-W42
- **Resolves:** FINDING-257
- **Extends:** ADR-016/024/137/165/176/263

## Context

Both public holdout splitters use positional slicing without checking the whole
source calendar. A rotated frame can yield internally sorted search and holdout
halves with the holdout entirely before search. A bounded public single-name sma
search on that source completes with one family, three evaluated configurations
and a failed verdict. A duplicate timestamp across the cut likewise appears once
in each locally unique half. Per-engine calendar checks cannot detect the ordering
relationship across two separate slices.

Normal ResearchDataset construction rejects these malformed source calendars and
isolates its retained frame. Cross-sectional full-panel asset_returns also rejects
the rotated source downstream; only its standalone splitter acceptance is shown.
No actual production occurrence, false graduate, historical cohort contamination
or calibration-rate change is established.

## Options considered

1. Validate original whole-index uniqueness/order at both public splitters: closes
   their own calendar-latest contract with two narrow guards and no source rewrite.
2. Validate only run_search: leaves standalone splitting and its panel analog weak.
3. Sort or deduplicate: changes evidence order or chooses among contradictory rows.
4. Require a UTC daily DatetimeIndex: broader metadata policy than this chronology
   defect, breaking ordered generic/naive compatibility preserved by ADR-176.

## Decision

Immediately after each splitter's existing holdout_fraction validation, require
original index.is_unique and index.is_monotonic_increasing. Refuse violations with
ValueError before length, slice or size work. Keep fraction refusal first; on a
malformed short calendar the calendar refusal intentionally precedes size refusal.

Preserve the entire existing fraction/floor arithmetic, size errors on valid
ordered input, original row/index/column values and order, and slice shapes.
Do not sort, deduplicate, normalize indexes, impose index types/timezones/cadence,
copy frames, or change scoring. Valid ordered empty/singleton indexes keep existing
size behavior. A singleton NaT is not an ordered calendar and now refuses earlier.

This guards strict source identity/order, not source provenance, actual elapsed
history, daily cadence, strategy causality or ownership of arbitrary mutable input.
The existing canonical production dataset boundary remains. No gate threshold,
search count recipe, estimator, selection rule, hash, accounting-v14, workflow,
generated record or frozen-cohort change. Existing valid source procedures stay
unchanged; no cohort is rerun, recertified or reinterpreted.

## Consequences, verification and reversal

A nonempty unique ordered prefix strictly precedes its nonempty held-out suffix.
Original duplicate identities cannot occur in both halves. TDD must observe actual
refusals missing before code, including rotated sorted halves, cross-cut duplicates,
descending/shuffled calendars and NaT. Verify original fraction precedence, valid
ordered generic/naive/aware indexes, exact split rows, source nonmutation and size
boundaries. Hypothesis checks both splitters' strict ordering and reconstruction
invariants. Include public run_search refusal before candidate work, independent
review and foreground make check-all before individual push and exact CI.

Remove only the two source-calendar guards to reverse, reopening FINDING-257.

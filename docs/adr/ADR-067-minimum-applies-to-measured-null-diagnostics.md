# ADR-067: Apply the null-comparison minimum to measured diagnostics

- **Status**: Accepted
- **Date**: 2026-08-29
- **Deciders**: Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Extends**: ADR-064 (matched-history null comparison)
- **Finding**: `docs/findings/FINDING-009-null-comparison-counts-unmeasured-rows.md`

## Context

ADR-064 refuses a real-vs-null comparison below `MIN_MATCHED = 30`. Its implementation counts
history-matched experiments, not the non-null finalist diagnostics from which each statistic's
median is computed. A cohort of 40 rows with five recorded walk-forward values currently publishes
a five-observation median as comparable. When the matched statistic is entirely absent, the
visible median falls back to the pool-wide population and can still be marked comparable.

`NullComparison` already exposes both quantities: `matched_n` is the history cohort and `real_n` is
the number of diagnostic observations in the displayed median. Only the latter measures whether
the statistic meets the sample floor.

## Decision

Preserve ADR-064's threshold of 30 and require at least 30 **non-null finalist diagnostics from the
matched-history subset** for each statistic to be comparable. The mismatch reason states the
measured diagnostic count. History-cohort size and diagnostic sample size remain separately
visible.

When a matched subset has no measured value, the report may retain its existing pool-wide fallback
as context on a refused row, but the fallback contributes zero matched diagnostics and cannot
satisfy comparability. Search-family and history checks are unchanged.

No gate criterion, calibration result, experiment schema, or generated artifact changes.

## Alternatives considered

1. **Keep counting history matches.** Rejected: membership in the cohort is not an observation of
   the statistic whose median is being judged.
2. **Drop rows with no matched diagnostic entirely.** Rejected: the refused row and its reason make
   missing measurement visible; silence would hide why the comparison disappeared.
3. **Lower the minimum when diagnostics are sparse.** Rejected: sparse measurement is not evidence
   that a noisier median is adequate, and weakening a validation threshold is prohibited.

## Consequences

- `comparable=True` now certifies both population identity and the stated minimum effective sample.
- Walk-forward and purged-CV comparisons can differ in comparability when their missingness differs,
  which accurately reflects that they are separate measurements.
- Historical data remains untouched.

## Reversal

Remove the matched-diagnostic count from `_mismatch` and again apply `MIN_MATCHED` only to
`len(matched)`. That intentionally restores FINDING-009.

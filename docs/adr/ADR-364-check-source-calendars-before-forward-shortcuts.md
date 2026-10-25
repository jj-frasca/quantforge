# ADR-364: Check source calendars before forward shortcuts

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session30, ISO2026-W43
- **Resolves:** FINDING-304
- **Extends:** ADR-168, ADR-176, ADR-255, ADR-363

## Context

Three raw forward wrappers can emit zero scores or holds before reaching their
engines' original source-calendar checks. Duplicate or descending dates entirely
before freeze pass these shortcuts despite failing the engines' identity rule.
No measured noncausal return or affected production decision is established.

## Options considered

1. Apply the existing native unique/ascending predicate at the raw wrappers.
   This validates calendar identity before a shortcut while retaining the original
   calculation body and all valid input domains.
2. Invoke the engine before checking for forward bars. This also performs price,
   strategy and numerical work the shortcut never required, broadening the change.
3. Sort or deduplicate inputs. This transforms the supplied observation order or
   silently chooses among conflicting observations.
4. Trust production preparation. Checked datasets protect managed callers but
   direct raw-frame/panel entry points remain available and inconsistent.

## Decision

Require native `index.is_unique` and `index.is_monotonic_increasing` at three
wrapper boundaries, before existing calendar maximum or cutoff access:

- `score_forward`: after frozen-column checks and existing optional-evidence
  reconstruction and frozen-symbol checks.
- `evaluate_cross_sectional_lifecycle`: after policy and frozen-column validation.
- `evaluate_lifecycle`: after policy validation.

Raise `ValueError` using the corresponding existing engine calendar message.
Add only the two-line predicate/error at each site; preserve every other statement.
Do not introduce a helper or change engines, paired-return validators, checked
single-name `evaluate_forward`, model schemas, price validity, position
reconstruction, timezone/cadence requirements, data normalization or arithmetic.

Empty/singleton ordered source indexes retain their native behavior. Existing
empty/naive lifecycle holds remain; existing empty/naive score failures stay.
Generic timestamp-object and offset-aware inputs remain, without inventing support
for generic integer cutoff comparisons. NaT calendars refuse through the same
native ordering predicate as the engines.

## Consequences and reversal

No-forward output no longer bypasses original calendar identity. Measured invalid
sources may refuse earlier, with preserved policy/column and early evidence-check
precedence. Score-root evidence common-revision checks remain later as before;
this decision does not move them ahead of calendar validation.
Valid matching inputs retain exact formulas, decisions, defaults, reason text,
policy hashes and thresholds. Native ordering is not source provenance, actual
cadence, causal strategy certification, or a new calibration measurement.
No generated record, frozen cohort, accounting-v14 or broker action changes.

Remove the three wrapper calendar guards to reverse this extension and reopen
FINDING-304.

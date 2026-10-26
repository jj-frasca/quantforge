# ADR-377: Require finite fundamental-screen minima

- **Status:** Accepted
- **Date:** 2026-10-26
- **Deciders:** Codex autonomous session 3, ISO2026-W44; research/data review
- **Resolves:** FINDING-319
- **Extends:** ADR-017 and ADR-372

## Context

Validated FundamentalCriteria permits NaN minima that silently admit negative
finite growth or margin through enabled checks. Independent synthetic witnesses
confirm both fields, with the other check disabled or both NaN simultaneously.
No affected real hunt or false graduate is established.

## Options Considered

1. **Require finite non-null numbers on FundamentalCriteria.**
   - Pro: covers ordinary direct and JSON construction with one model policy.
   - Con: previously accepted infinite minima also refuse, even when their
     comparisons were determinate; callers must express policies with finite values.
2. **Guard NaN only in screen_fundamentals.**
   - Pro: addresses direct consumers, including unchecked configuration copies.
   - Con: leaves invalid config evidence constructible and requires new runtime
     failure semantics in a function that currently returns a screen verdict.
3. **Constrain minima and validate every fundamental data model together.**
   - Pro: supplies a broader numeric contract.
   - Con: rejects existing finite policies and changes provider/error boundaries
     without evidence or review for those separate decisions.

## Decision

Add only allow_inf_nan=False to FundamentalCriteria's existing ConfigDict,
retaining frozen=True. Preserve both nullable fields, all finite values and
constructor coercions, default zero, None-disabled checks and native screen
comparisons/reason formatting. No graduation threshold, parser, snapshot,
provider, search, workflow or accounting-v14 change is adopted.

## Consequences

Ordinary validated direct and JSON construction refuse nonfinite minima before
those minima can define a screen. None remains deliberate check disablement;
missing source metrics retain their current failure reasons. Existing instances
and unchecked copies are outside this constructor-only guarantee. Source numeric
validity and historical provenance require separate review. No generated record
is rewritten or calibration executed.

Write and observe failing direct/JSON tests before source edits. Preserve finite
and None controls through exact prepatch replay, a Hypothesis round-trip invariant
and frozen screen-decision controls. Independently review final source/data contracts and
run foreground make check-all before individual publication. Reversal removes
only the added ConfigDict keyword, reopening FINDING-319.

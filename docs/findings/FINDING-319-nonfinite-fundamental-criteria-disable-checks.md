# FINDING-319: NaN fundamental minima silently disable enabled checks

- **Status:** Corrected (ADR-377)
- **Date:** 2026-10-26, Codex autonomous session 3 (ISO2026-W44)
- **Severity:** Medium for malformed fundamental-screen configuration
- **Affected:** FundamentalCriteria validated construction and JSON loading
- **Related:** ADR-017, ADR-372, FINDING-315

## Evidence

FundamentalCriteria accepts NaN for either min_revenue_growth_yoy or
min_net_margin. For an enabled check, the comparison `metric < minimum` then
returns false for finite negative evidence. A synthetic snapshot with growth
-0.5 and net margin -0.5 fails both default zero minima, but passes with no
reasons when both minima are NaN. With the other check explicitly disabled by
None, either individual NaN minimum independently admits its negative metric.
Parent, independent research and independent data-engineering probes confirmed
the behavior without provider calls or searches.

This is the ADR-017 fundamental screen, distinct from the optional quality/value
pre-screens corrected by ADR-372. Missing metric values already fail enabled
checks, and None minima deliberately disable their checks. NaN is neither of
those states. No affected real hunt, false graduate or calibration outcome is
established. The synthetic witness does not implicate a graduation threshold.

## Correction and limits

ADR-377 requires finite non-null criteria fields at ordinary validated
construction and JSON loading. Reject NaN and both infinities rather than
substituting None, zero or another minimum. Preserve all finite thresholds,
including negative and large values, normal constructor coercions, default zero,
frozen configuration, None-disabled checks and existing screening arithmetic.

Unchecked model_copy/model_construct inputs and separate FundamentalSnapshot
numeric validity remain outside this constructor correction. No source parser,
missing-data fallback, provider, search, gate, accounting identity, historical
record or generated file changes. This does not establish source provenance or
point-in-time availability.

## Verification

Before the source edit, 24 direct/JSON nonfinite cases failed because no
ValidationError was raised, while 14 finite/default/None controls passed. After
the single ConfigDict keyword was added, 65 focused synthetic tests passed.
Hypothesis checks exact finite-float JSON round trips, including signed zero
and the full finite binary64 domain.

The prepatch replay exactly matched 81 config payloads/JSON outputs, 486 screen
results and the entire module AST after stripping only the adopted keyword.
Independent research review repeated all 65 focused tests and the replay; data
review repeated 43 focused tests and the replay. Both approved the final scope.
The research review corrected an ADR test-description overstatement before
publication; screen-decision controls are fixed replay, not a Hypothesis claim.

Foreground make check-all passed 15,050 backend tests (97.43% coverage), 746
frontend tests (97.88%) and all lint/format/type gates. Logs are
/tmp/qf-w44-s3-criteria-red.log, /tmp/qf-w44-s3-criteria-green.log and
/tmp/qf-w44-s3-check377.log. No generated file or calibration was written.

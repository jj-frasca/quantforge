# FINDING-315: Nonfinite optional pre-screen thresholds admit weak scores

- **Status:** Corrected (ADR-372)
- **Date:** 2026-10-25, Codex autonomous session34 (ISO2026-W43)
- **Severity:** Medium for malformed opt-in universe admission
- **Affected:** QualityGateConfig, ValueGateConfig and their CLI parsers
- **Related:** ADR-023, ADR-029

## Evidence

Both optional pre-screen configs accept a NaN minimum, directly and through the
CLI numeric override. A synthetic score of 0.1 fails the finite default minimum
0.5 but passes the same enabled screen with minimum NaN: the comparison
`score < minimum` is false, leaving no failure reason. Negative infinity also
admits every finite score; positive infinity rejects every scored name.

Parent and independent research probes reproduced the NaN case through both
actual parsers and run_universe_hunt. With injected score providers, only the NaN
case reached a frame-provider sentinel; the finite control was filtered first.
The sentinel stopped before search, so all probes produced zero experiments.
No real provider, search, calibration or generated-data write was performed.
Both screens remain off by default. No affected real hunt or false graduate is
established, and no graduation threshold is implicated by this witness.

Receipts: /tmp/qf-w43-s34-prescreen-prospective-parent.json and
/tmp/qf-w43-s34-prescreen-nan-research.{py,json,md}.

## Correction and limits

ADR-372 requires finite threshold fields at validated config construction,
including JSON and CLI paths. Reject malformed numeric evidence rather than
turning it into an absent screen, symbol token or substituted cutoff.

Preserve every finite threshold, including existing values outside [0,1], current
coercions, optional flags, default 0.5, config hashes, CLI grammar and screen
arithmetic. This is input validity, not threshold calibration. Direct unchecked
model copies and the separate validity of supplied score models are outside this
constructor correction; it does not certify arbitrary in-process evidence.

Before adoption, independent controls froze two complete module ASTs, 144 config
payloads/JSON/hashes, 1,008 screen results and 18 CLI cases. The corrected read-only
replay helper loads fixture declarations without re-executing the NaN witness or
rewriting receipts. Its pre-adoption control matched exactly. Future replay may
strip only the two adopted ConfigDict keywords before comparing whole modules.

## Verification

Before either source edit, the new tests observed 36 failures and four passing
finite/default controls. After the two ConfigDict changes, the focused synthetic
suite passed 104 cases with two live cases deselected. Independent final research
review approved all six paths and repeated 83 relevant synthetic cases with two
live cases deselected.

The preservation replay exactly matched both whole-module ASTs after stripping
only the two adopted keywords, all 144 finite config payloads/JSON/hashes,
1,008 screen outputs and 18 CLI cases. It performed no provider calls or receipt
rewrites. Hypothesis verifies exact finite-float and hash round trips through
JSON, including the full finite float domain rather than only [0,1].

Fresh foreground make check-all passed 14,878 backend tests (97.42% coverage),
746 frontend tests (97.88%) and all lint/format/type gates. Logs:
/tmp/qf-w43-s34-prescreen-red.log,
/tmp/qf-w43-s34-prescreen-synthetic-green.log and
/tmp/qf-w43-s34-check372.log. No threshold value, scoring formula, default,
accounting identity, frozen calibration or generated record changed.

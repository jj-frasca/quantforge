# FINDING-316: Nonfinite valuation evidence can pass a finite value screen

- **Status:** Corrected (ADR-373)
- **Date:** 2026-10-25, Codex autonomous session34 (ISO2026-W43)
- **Severity:** High for malformed valuation evidence; no production occurrence established
- **Affected:** UndervaluationScore construction and final score_valuation output
- **Related:** ADR-022/023/124/147/155 and FINDING-315

## Evidence

Ordinary model validation accepts a NaN composite score. The finite default value
screen then passes it because `NaN < minimum` is false. A finite score of 0.9 with
NaN margin of safety also passes require_margin_of_safety=True because `NaN <= 0`
is false. No unchecked model copy is needed. JSON serialization changes these
nonfinite values to null, losing the distinction between invalid evidence and
genuine missingness. ADR-372 guards config minima, not these separate inputs.

An independent actual-producer witness uses two accepted annual input models
with finite revenue, net income and free cash flow of 1e308, EPS 1, diluted shares
1e6 and historical/current price 10. With default DCF assumptions, native
accumulation produces infinite intrinsic value, NaN margin and NaN composite,
with no flags. Both finite screen configurations pass. A normal-size control
remains finite. This extreme synthetic input establishes an implementation path,
not plausible corporate scale, vendor truth, economic consistency of those input
fields, an actual provider occurrence, a false graduate or a trading effect.

Scratch evidence: /tmp/qf-w43-s34-value-evidence-prospective.{py,json,md}.
Independent research and data reviews support ADR-373's narrow constructor policy.

## Correction and tradeoffs

Require finite numeric evidence on ordinary constructor/dictionary and JSON
validation, including the unchanged producer's final new-model construction. Keep
nullable absence, every finite value/coercion, flags shape and valuation arithmetic.
Do not recover extreme arithmetic, add score bounds or replace refusal with None.

Provider construction errors propagate into the hunt's existing per-symbol error
handling even when the optional screen is off: valuation is record-first. This
skips downstream hunt acquisition/search, but the earlier value provider may
already have acquired prices/frames. The fundamental sweep calls its scorer
outside a containing per-record error catch, so a new refusal can abort its shard
before writing. Accept that explicit availability cost rather than fabricate an
unscored company or silently change workflow recovery policy.

Existing instances, unchecked copies, deep flag immutability, score bounds and
other estimator contracts remain outside scope. Historical nulls cannot reveal
whether an old nonfinite value was serialized away. No generated record is repaired.

Pre-adoption controls freeze 89 finite/coercion/nullable model payloads, 12 ordinary
producer payloads, 30 persisted valuation leaves, 611 source hashes and the whole
score.py AST. The read-only control matched exactly. Receipt and replay:
/tmp/qf-w43-s34-value-constructor-baseline.{py,json}.

## Verification

The new synthetic tests observed 58 failures and 17 finite/null controls before
implementation. All 75 new cases pass after the one-keyword change, including
all nine numeric fields through direct/JSON paths, finite Hypothesis round trips,
nullable auxiliaries, actual producer overflow, provider propagation and hunt
errors with screening off/on. The focused suite passed 178 synthetic cases with
two live cases deselected; 35 core valuation cases also passed.

Independent research and data final reviews approved all six paths. Research
repeated 135 synthetic tests with two live cases deselected and the strict replay.
Both parent and independent replay exactly preserved the 89 finite model cases,
12 ordinary producer cases, 30 persisted valuation leaves and 611 source hashes;
the whole score.py AST matches after removing only the adopted ConfigDict keyword.
These controls are bounded compatibility evidence, not general source certification.

Fresh foreground make check-all passed 14,953 backend tests (97.42% coverage),
746 frontend tests (97.88%) and all lint/format/type checks. Logs:
/tmp/qf-w43-s34-valuation-red.log, /tmp/qf-w43-s34-valuation-green.log and
/tmp/qf-w43-s34-check373.log. No generated record, DCF/scorer arithmetic,
calibration identity, default or validation threshold changed.

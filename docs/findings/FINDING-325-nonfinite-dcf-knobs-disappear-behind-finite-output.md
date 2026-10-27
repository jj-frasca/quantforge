# FINDING-325: Nonfinite DCF knobs can disappear behind finite valuation output

- **Status:** Corrected — ADR-382 ordinary validated configuration
- **Date:** 2026-10-27, Codex autonomous session5 (ISO2026-W44)
- **Severity:** Invalid configuration can alter finite financial output silently
- **Affected:** DcfAssumptions construction/JSON and its intrinsic-value consumer
- **Related:** ADR-022/382; distinct from FINDING-315/316 and FINDING-323

## Evidence before correction

At producing revision 0bad09b6, ordinary DcfAssumptions validation permits NaN
growth bounds. Native min/max comparisons can ignore the invalid bound without
warning, so the unchanged producer returns a finite value. ADR-373's finite
UndervaluationScore boundary cannot detect configuration that has already been
lost. ADR-372 concerns separate screen minima, not these financial assumptions.

A synthetic two-year history with free cash flow 100 to 120, shares 10 and current
price 100 produces 12% growth under default clamping. With max_growth=NaN the
producer uses approximately 20%, and score_valuation returns a finite score
0.6986823604566542 with no DCF flags. Reversing the cash flows to 120 then 100
with min_growth=NaN uses approximately -16.67% instead of the default lower
clamp of zero; valuation output remains finite. No source acquisition is needed.

An independent research control with 100 to 110 cash flow shows another failure
mode: either NaN bound yields exactly the ordinary finite output, so numerical
output checks cannot identify the malformed assumptions even when results happen
to match. Nested IntrinsicValueResult JSON serializes the invalid knob as null;
DcfAssumptions cannot reload that null because the field is nonnullable. NaN
rate/terminal settings can also pass assumptions construction, although ADR-373
already refuses their resulting nonfinite valuation output in the checked path.

Parent receipt: /tmp/qf-w44-s5-dcf-assumptions-parent.json. Independent data receipt:
/tmp/qf-w44-s5-dcf-assumptions-independent-data-engineer.json; research draft:
/tmp/qf-w44-s5-dcf-assumptions-research-draft.md. These are synthetic configuration
and producer witnesses, not evidence of an actual provider run, experiment,
false graduate, trading effect or plausible business valuation.

## Decision and limits

ADR-382 requires finite floats on ordinary DcfAssumptions construction,
dictionary/JSON loading and raw nested validation. Preserve all finite inputs,
coercions, defaults, the existing discount>terminal comparison, growth ranges,
projection counts, JSON fields and financial arithmetic. No default/None recovery
or new economic/range/order policy is adopted. Previously accepted inverted
finite bounds and zero/negative horizons remain outside this correction.

Both value-provider APIs forward explicitly supplied assumptions. Ordinary invalid
construction now refuses before injection; scoring stays outside their acquisition
fallback. No wrapper/catch behavior changes and no default CLI override incidence
is established. Existing instances and unchecked copies remain outside this
constructor boundary. Lost historical settings, complete assumption persistence
and general DCF model validity are separate concerns. No screen/graduation
threshold, parser, accounting-v14, generated record or frozen cohort changes.

## Verification

The prepatch baseline /tmp/qf-w44-s5-dcf-assumptions-baseline.{py,json} freezes
90 complete finite configuration/JSON/DCF/valuation claims and module source,
including finite coercions, inverted bounds and zero/negative horizon controls.
Before the sole production keyword edit, 44 tests failed for the expected missing
ValidationError and 17 controls passed (1.22 seconds). All 61 new tests passed
afterward, including direct/dictionary/JSON fields, raw nested results, actual
bound witnesses, finite Hypothesis JSON round trips and both provider controls.
Parent focused verification passed 222 synthetic tests with two live tests
deselected. Independent data ran 78 tests; research ran 122. Both approved all six
paths and replayed all 90 complete finite claims. The whole module AST is identical
after removing only DcfAssumptions.allow_inf_nan=False.

Foreground make check-all passed: 15,358 backend tests (97.43% coverage),
746 frontend tests (97.88% statement coverage), plus lint, formatting and types.
Logs: /tmp/qf-w44-s5-dcf-assumptions-{red,green,focused}.log and
/tmp/qf-w44-s5-check382.log. No historical configuration or generated data is repaired.

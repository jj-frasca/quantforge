# FINDING-232: Float64 large-origin centering corrupts both OLS coefficients

- **Status:** Corrected by ADR-283
- **Date:** 2026-10-13
- **Scope:** BenchmarkComparator, both-original native float64/classic Float64

## Reproduction

Use benchmark=pd.Series(float(2**60)+np.arange(4)*256,dtype=dtype) and
strategy=benchmark+256 for either dtype. Public comparator accepts beta
0.6666666666666666 and annual alpha9.684540638697531e19. Independent centered
Fraction OLS on original binary ratios gives beta1/alpha64512. Native variance
131072 and covariance87381.33333333333 disagree with exact matched moments
109226.66666666667. All published claims are finite, so finite validation misses
this precision defect. Alpha-only repair leaves the known false beta unchanged.

## Impact and correction

Descriptive slope/intercept evidence can be wrong for accepted represented inputs.
No contamination of historical market records is established, and these scalars
are not search/gate inputs. ADR-283 chooses coupled exact common-grid sufficient
sums for this bounded source family, preserving other coefficient paths and all
original noncoefficient statistics. Family-wide rounding changes intentionally.
Final unrepresentable coefficients must refuse; valid zero/subnormal rounding
remains. Other statistic precision/measurability limits are explicitly separate.

## Evidence

Before repository implementation, inherited read-only scope reproduced locally:
252 exact centered Fraction finite coefficient pairs/32 overflow refusals;
100k ordinary .187s/fullwidth .629s. Independent research-expert additionally
confirmed239finite/161overflow plus4zero/subnormal controls and conservative
~6600bit intermediate bound. Scope APPROVE before production. Initial public TDD127failed/56passed included
one reversed full-width pair misclassified as finite. Independent review corrected
that fixture before production: finite full-width identical sources, original
reversed pair retained as overflow, genuine subnormal plus half-subnormal tie-zero
controls. Final precode RED135failed/56preserved; implementation then191passed.

Final independent production review APPROVE:400public exact centered Fraction
coefficient pairs with exact affected other-output/error-state preservation;
578complete outside-family baseline comparisons (including Sparse) including unchanged refusal
outcomes;239finite/161overflow helper probes plus4rounding controls;191authored
tests GREEN; eight guard-precedence probes refuse before helper entry. Removing only new helper/predicate/dispatch restores baseline module
AST exactly. Final grid:int static annotation has no runtime effect; mypy181
modules and repeated191tests GREEN. All independent verification terminal.

Initial full gate refused only mypy's Any inference for the grid; adding its int
annotation corrected that type issue without runtime conversion or arithmetic
change. First backend-complete gate had13compatibility failures/10330passed: six old
Float64 constant-alpha expectations, three same-series overflowing covariance
refusal expectations, and four error-regex mismatches despite retained refusal.
Strengthened only affected legacy alpha expectations to exact Fraction means;
retained the full overflow Hypothesis domain and now require exact beta1/alpha0
and zero other statistics where final coefficients are representable. Unrepresentable
constant alpha still refuses. No tests removed/skipped or tolerance/domain relaxed.
Isolated published HEAD with strengthened tests:9genuineRED/73preserved. Final
273affected tests GREEN; final seven-path independent review APPROVE and repeated
400public/576outside/AST checks remain exact. Error text preserves the original
statistics-finite contract plus the new coefficient-specific assertion.
Final foreground make check-all PYTEST_WORKERS=4 passed:10343backend tests,
97.64%coverage;363frontend tests,97.63%statements;lint/format/mypy GREEN.
No generated evidence, validation thresholds or accounting identity changed.

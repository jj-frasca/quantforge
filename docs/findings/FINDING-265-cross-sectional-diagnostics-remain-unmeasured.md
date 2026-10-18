# FINDING-265: Cross-sectional split counts remain unmeasured diagnostics

- **Date:** 2026-10-18
- **Severity:** Medium — documentation overstates evaluation scope
- **Status:** Open for evaluator integration; documentation scope corrected
- **Reviewed source:** 1018ca7c, cross_sectional/search.py::_build_report
- **Related decisions:** ADR-024/035/038/039

## Evidence

The cross-sectional report assembler calls walk_forward_splits and
purged_kfold_splits, stores their lengths and never calls either evaluator.
ValidationReport.walk_forward and purged_cv default to null. CrossSectionalTrial
construction also omits the inherited walk_forward_oos_sharpe and
purged_cv_oos_sharpe fields. A split count certifies geometry, not evaluated
selection, OOS returns, Sharpe or a paired benchmark.

Independent direct report assembly on an explicit finite 24x2 matrix and parent
assembly on a different 60x3 matrix both produce three walk-forward splits and
three purged folds while leaving both diagnostic objects null. The first also
has empty flags/interpretations. These witnesses call only the report assembler;
no parameter search, random source, vendor, calibration or generated record is
created or inspected. Source inspection confirms the production trial omissions;
no prevalence count over historical experiments is asserted.

Receipts and executable reproduction:
/tmp/qf-w42-s31-xs-diagnostics-review.md,
/tmp/qf-w42-s31-xs-diagnostics-review.py,
/tmp/qf-w42-s31-xs-diagnostics-review.json,
/tmp/qf-w42-s31-xs-diagnostics-parent.json.

## Scope and disposition

Architecture and validation cold memory described the longitudinal evaluation
without distinguishing this cross-sectional path. Those descriptions now state
the boundary explicitly. Immutable ADR-038's every-report intent remains an
implementation gap here; the documentation correction does not complete it.
Null is unmeasured and must never be interpreted as a measured zero.

The frontend already renders absent walk-forward as "not measured" and absent
purged CV as "folds, not scored". No UI correction is justified. Cross-sectional
PBO, whole-search DSR, parameter stability, rank IC and locked-holdout evaluation
remain implemented. Neither missing diagnostic is a required graduation
predicate; this witness establishes no incorrect gate verdict or false graduate.

Do not synthesize scores from counts or reuse longitudinal calibration as a
cross-sectional result. Future evaluator integration requires an ADR specifying
factor selection, matched benchmark and embargo semantics, followed by TDD and
appropriate evidence. This documentation-only correction changes no runtime,
model, test, selector, threshold, identity, generated record or frozen cohort.

## Verification

Parent and independent direct witnesses and source review passed. Independent
final review approved all three documentation paths, including the second
longitudinal qualification in cold-memory section 7.5. Backend, frontend, tests
and data remained byte-unchanged. Fresh foreground make check-all passed 12,866
backend tests (97.39% coverage), 438 frontend tests (97.69% statements), lint,
formatting and strict types. Log /tmp/qf-w42-s31-check265.log; all local checks
closed successfully. Exact master CI is verified after individual publication.

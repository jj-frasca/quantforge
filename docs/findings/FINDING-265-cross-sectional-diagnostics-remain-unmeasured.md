# FINDING-265: Cross-sectional split counts remain unmeasured diagnostics

- **Date:** 2026-10-18
- **Severity:** Medium — documentation overstates evaluation scope
- **Status:** Open in part; backend and public walk-forward measurement delivered
  by ADR-321/322; purged evaluation and dependency/embargo design remain open
- **Reviewed source:** 1018ca7c, cross_sectional/search.py::_build_report
- **Related decisions:** ADR-024/035/038/039

## Original evidence at 1018ca7c

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

## Original scope and disposition

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

## Original verification (2026-10-18)

Parent and independent direct witnesses and source review passed. Independent
final review approved all three documentation paths, including the second
longitudinal qualification in cold-memory section 7.5. Backend, frontend, tests
and data remained byte-unchanged. Fresh foreground make check-all passed 12,866
backend tests (97.39% coverage), 438 frontend tests (97.69% statements), lint,
formatting and strict types. Log /tmp/qf-w42-s31-check265.log; all local checks
closed successfully. Exact master CI is verified after individual publication.

## ADR-321 backend walk-forward correction (2026-10-19)

The new producer evaluates each full allocated family matrix with the unchanged
walk-forward evaluator. Config choice uses each expanding train block; the chosen
column continues on its next test block. One search-only equal-weight universe
benchmark is scored on the same test rows for every family. Full results stay in
ephemeral reports, while trial means persist with a common paired benchmark,
recognized method and actual search-bar/split counts. Method-null historical and
unpaired scalar records remain readable; no score or method is backfilled.

The recognized measured branch refuses missing family means, absent/nonfinite
benchmark, invalid original geometry or an empty trial population. Existing
store reconstruction protects against unchecked incomplete model copies.
Producer consistency checks establish common benchmark and geometry; compact
scalars do not preserve every window's selected config or prove provenance.
Numerically unmeasurable diagnostic blocks now refuse a search rather than
fabricating a number. Primary-output preservation is therefore conditional on
measurable diagnostics, not an unchanged complete success domain.

This closes the backend walk-forward portion only. Purged CV remains unmeasured
until factor dependency spans and embargo semantics are designed separately.
The reduced cross-sectional API and dashboard are unchanged by this slice.
Longitudinal null/power distributions are not panel calibration, and no cohort
or generated artifact is rerun or relabeled.

Publication review also qualifies the original frontend sentence above: the
separate validation-report renderer labels absent diagnostics, while the actual
CrossSectionalPanel has no walk-forward or purged diagnostic column/caption.
That renderer does not certify public panel measurement or publication.

These family-local scores do not evaluate train-only cross-family selection:
the eventual family winner still uses the complete search sample. Static
fundamental maps remain conditional supplied snapshots, not historical
point-in-time evidence. Existing internal config costs continue through slices;
entry/switching trades for a common account are not reconciled. The equal-weight
universe benchmark has no added turnover-cost model. Scores remain equal means
of window Sharpes, never Sharpe on a stitched trading policy.

Three deterministic prechange primary payloads are frozen at
`/tmp/qf-w43-s1-xs-wf-baseline.json`, SHA256
`f54f294ef6976387060dabd2fa39dce2f67f5c65db2313a6060fbeec4d6ad096`.
They cover two price-only families, a supplied static value family, different
quantile allocations and carried prior counts. The projection excludes only
new diagnostic fields and run UUID/time. Source before the correction:
`8d341417caa4c9e9f33cf6d9e4580877228fb9feaf82cd784a09a12622c8c90a`.

Actual preimplementation RED observed 34 failures in 7.29 seconds with the
production diff empty (`/tmp/qf-w43-s1-xs-wf-red.log`). All 34 then passed.
Five supplementary postimplementation controls exercise actual unmeasurable
training moments and missing/unequal benchmark or actual split geometry; these
are supplementary GREEN evidence, not preimplementation RED. The final focused
regression run passed 278 tests in 23.12 seconds, including all 39 new cases;
Ruff, formatting and strict mypy passed. The verification summary is
`/tmp/qf-w43-s1-xs-wf-green-receipt.json` (a summary, not captured raw stdout).

Parent audit preserved all three frozen primary payloads exactly, six unchanged
helper/class ASTs, all four original experiment methods, all original primary
report statements and the complete search AST after removing only the new
diagnostic insertions/keywords and its leading docstring. The clarified report
docstring is also excluded precisely. Ten core modules, including the gate,
accounting, budget, portfolio kernel, registry, evaluators, PBO, primary metrics
and holdout, retain their bytes. Bounded controls establish preservation on
these fixtures, not universal equivalence of every possible native input.
Audit: `/tmp/qf-w43-s1-xs-wf-parent-audit.py` and
`/tmp/qf-w43-s1-xs-wf-parent-audit-final.log`.

The first full gate found seven failures in existing original-trial-count
fixtures (13,047 passed). Their legacy report stub intentionally stops at
repricing to verify actual Python-int lifetime addition; the new pairing check
ran before that interception. Only the new consistency block moved downstream
of unchanged repricing and immediately before holdout. The count tests remain
unchanged, real evaluator failures still propagate at family assembly, and
inconsistent evidence still refuses before holdout/publication. The refreshed
count-plus-new suites pass 175 tests in 4.92 seconds and broader focused suites
pass 278 in 22.53 seconds; Ruff/format/mypy pass. Raw logs:
`/tmp/qf-w43-s1-xs-wf-primary-order-green.log` and
`/tmp/qf-w43-s1-xs-wf-primary-order-focused-green.log`.
Refreshed primary AST, exact three payloads and all ten core hashes pass.

All 25 current cross-sectional pool rows pass construction and full JSON
roundtrip; source SHA256 remains
`4c3a79182a923cbe98c270e693beea2175be3acc0337f8277e7d968b67a10ee1`.
This is compatibility evidence, not validation of those historical observations.
Receipt: `/tmp/qf-w43-s1-xs-wf-pool-compatibility.json`.
Final source SHA256:
`e8c5e113853b98a178c0b51e8d980efae2619e3a7778d86397c1f50205b7800e`.
Independent final research review approved all seven paths, reran all 39 new
cases and checked a separate hand-calculated two-window oracle: selected
configs [0,1], paired benchmark mean 1.79512050490173 versus whole-history
benchmark Sharpe 1.2591025250114283. Refreshed review reran all 175 count/new
tests in 3.58 seconds and reversed only the block relocation in memory to
recover the previously reviewed source hash exactly. Fresh foreground `make check-all PYTEST_WORKERS=4` completed successfully:
13,054 backend tests (97.40% coverage), 438 frontend tests (97.69% statements),
lint, formatting and strict typing green. All checks closed. Full-gate log:
`/tmp/qf-w43-s1-check321-final.log`. This completes backend walk-forward
measurement; purged evaluation and API/dashboard publication remain open.

## ADR-322 attributed public publication (2026-10-19)

The follow-up adds exact stored family means, common paired benchmark, recognized
method and actual search/split geometry to the latest-experiment read-only API.
The source experiment reconstructs before projection. Public models and the
existing client parser enforce coherent finite measured metadata without
recomputing scores or graduation. Legacy null/omitted fields stay readable,
and method-null nonnull family scalars remain explicitly legacy and unpaired.
No method, benchmark, geometry or historical measurement is synthesized.

The panel adds one mean walk-forward Sharpe column and a shared caption for the
equal mean of same-window equal-weight universe benchmark Sharpes and actual
search-bar/window counts. Missing means read not measured. Legacy unpaired
scalars receive no paired caption or inferred excess. Visible qualifications
retain whole-sample family winner selection, fixed-config continuation/internal
costs without account entry/switch reconciliation, benchmark without extra
turnover costs, static supplied fundamental snapshots without historical PIT,
and equal means of window Sharpes rather than stitched-policy Sharpe. Purged CV
still reads not measured, with no invented historical fold count.

All 25 current primary API views were frozen before publication changes at
`/tmp/qf-w43-s1-xs-api-primary-baseline.json`, SHA256
`af477b989965986022dacde710e863d8ed9282fa2fa806c8a44d85d056fca36e`.
The projection excludes only new diagnostic fields; twelve research modules,
including the ADR-321 evaluator producer, are frozen for byte-preservation checks.

Backend actual preimplementation RED observed 25 failures and 2 preserved
controls in 2.79 seconds, with the production API diff empty. Frontend actual
preimplementation RED observed 41 failures and 95 preserved controls before
either runtime client file changed. Logs:
`/tmp/qf-w43-s1-xs-wf-api-red.log` and
`/tmp/qf-w43-s1-adr322-frontend-red.log`.

Review found an additional boundary gap in the new, uncommitted public view:
unchecked copies bypassed finite and original-count field checks when the root
model trusted instantiated copies. A separate test-first slice observed four
failures for NaN/infinite benchmark, floating bar count and boolean split count
before adding only root-view `revalidate_instances="always"`. Nested trial views
already revalidate. This is an implementation-time correction, with no released
measurement affected. The supplementary RED log is
`/tmp/qf-w43-s1-xs-wf-api-revalidate-red.log`.

Final backend focused verification passes 87 tests including all 31 new API
cases, with Ruff/format/mypy green. All 136 targeted frontend tests, ESLint and
TypeScript pass. Parent independently reran the 136 frontend tests (2.66 seconds)
and reviewed their rendered-value/legacy/error-state controls. Independent
scientific review approved all twelve paths and independently reran the 31 new
API cases (2.28 seconds). One stale active-document publication-open clause was
corrected during review. Raw GREEN receipts:
`/tmp/qf-w43-s1-xs-wf-api-revalidate-green.log`,
`/tmp/qf-w43-s1-adr322-frontend-green.log` and
`/tmp/qf-w43-s1-adr322-parent-frontend.log`.

All 25 frozen primary API views remain exact after removing only the new fields;
all twelve research modules retain their bytes, including the ADR-321 producer.
Generated source bytes remain unchanged. Audit:
`/tmp/qf-w43-s1-xs-publication-audit.py` and
`/tmp/qf-w43-s1-xs-publication-audit-final.log`.
Final API source SHA256:
`80c0a9fdf95c46df01b538de7b2624d8d14db8d743623530c0b8eaa135913242`.
Client schema SHA256:
`a1cc418ac2ede8e8c7fab199ff1016d55443dab6ff5b2ca032021deb84597bfc`.
Panel SHA256:
`94751bdced8308e843fe2af88361f852998632a96aac11bc2c422b95e2febf2b`.
Fresh foreground `make check-all PYTEST_WORKERS=4` completed successfully:
13,085 backend tests (97.41% coverage), 479 frontend tests (97.72% statements),
lint, formatting and strict typing green. All checks closed. Log:
`/tmp/qf-w43-s1-check322.log`. This completes attributed public walk-forward
publication; purged evaluation and its dependency/embargo design remain open.
No evaluator, selector, threshold, accounting-v14, generated file, frozen cohort
or workflow is changed by this publication slice.

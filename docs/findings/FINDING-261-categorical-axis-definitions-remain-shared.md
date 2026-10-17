# FINDING-261: Deep frame snapshots share categorical axis definition owners

- **Date:** 2026-10-17
- **Status:** Resolved — ADR-306
- **Area:** shared frame-copy recipe, categorical row/column axis storage

## Reproduction

Both public splitters accept eight ascending unique categorical row labels with
numeric categories 0..7. After a four/four split, source/search/holdout category
arrays share memory despite explicit index.copy(deep=True). Starting from
search.index.categories.to_numpy(copy=False), follow public NumPy base links to
the writable owner. Setting coordinate 4 to 123456 changes the first held-out label
and source label 4 to 123456. Categorical column axes and categorical MultiIndex
levels share the same route. Numeric price arrays remain unchanged and isolated.

Independent ten-case probe: `/tmp/qf-w42-s25-axis-category-probe.py` and JSON receipt.
Parent independently reproduced both splitter label mutations with unchanged prices:
`/tmp/qf-w42-s25-categorical-parent-probe.json`.
Report: `/tmp/qf-w42-s25-axis-category-finding.md`.

## Attribution and limits

Categorical codes themselves are copied. Category definitions remain shared; these
numeric axis buffers are distinct from excluded recursive mutable Python objects.
Canonical DatetimeIndex and ordinary numeric/date MultiIndex storage passed negative
controls. Plain/range/datetime/timedelta/period/interval axes showed no additional
alias in the bounded family review. This does not certify every extension family.

Unused category/level metadata can contain labels absent from a portion. That alone
is normal metadata, not a price leak; no category pruning is justified. Pandas can
cache derived index lists, so mutation probes also inspect raw category owners and
actual scalar labels without a pre-mutation list cache.

No canonical production occurrence, current catalog exploitation, actual price leak,
historical corruption, false graduate or changed calibration rate is established.
ADR-304's price-buffer correction remains valid. These synthetic ownership probes
perform no strategy search, vendor access or historical/frozen-source replay.

## Correction and verification

ADR-306 recursively copies categorical definitions and MultiIndex levels inside the
existing shared copy helper. It preserves exact categories, codes, names, order,
unused metadata and dtype while leaving ordinary axis copying and numeric copying
unchanged. No split guard, scoring, threshold, default, hash or v14 change.

Before adoption, the scratch public-pandas recipe passed 30 exact frame/axis and
actor-mutation cases. A separate review passed 22 family/recipe cases plus eight
NA/unordered/name/unused/two-categorical-level cases. Receipts:
`/tmp/qf-w42-s25-axis-category-recipe.json` and
`/tmp/qf-w42-s25-axis-family-review.md`. NA cases test helper compatibility, not
calendar admission. An initial scratch datetime mutation harness raised TypeError
before completion; the corrected int64-view harness passed, with chronology
preserved in the scratch report. These are bounded checks, not universal certification.

The actual pre-production run failed 94 cases with 12 preservation controls
passing in 19.30 seconds (`/tmp/qf-w42-s25-category-actual-red.log`). Failures
exercise public category-owner sharing/mutation through copy_frame and both
splitters. An earlier test collection attempt raised a runtime Index[Any]
annotation TypeError; adding deferred test annotations fixed collection before
production edits. That collection error is preserved separately and is not RED
evidence. Implementation began only after the genuine failing run completed.

Focused verification passed 389 tests (106 new and 283 existing), with three
existing timedelta deprecation warnings. The initial GREEN, type/style and
payload receipts remain preserved. Parent review then removed a production-wide
deferred-annotations import, quoting only the new helper's annotations, so the
existing functions retain their exact runtime annotation metadata. Final reruns
again passed all 389 tests in 8.22 seconds, Ruff/format, mypy184 and all four
frozen standalone scientific payload comparisons. Final receipts use the
`/tmp/qf-w42-s25-category-*-final2.log` paths; chronology and source hashes are in
`/tmp/qf-w42-s25-category-implementation-review-final2.md` and
`/tmp/qf-w42-s25-category-source-freeze-final2.json`.

Parent source/test/document review approves the narrow recipe. The exact AST and
byte audit `/tmp/qf-w42-s25-source306.json` confirms only the private helper and
two axis delegations changed executable frame code; original function annotations,
all other frame AST, dataset/splitter bytes and existing tests remain unchanged.
Four fixture matches establish bounded regression preservation, not new calibration
or universal numerical equivalence. Fresh session25 foreground `make check-all`
completed successfully: 12,495 backend tests, 97.41% coverage; 381 frontend tests,
97.66% statements; all Ruff, formatting, mypy184, ESLint and TypeScript checks green.
Log: `/tmp/qf-w42-s25-check306.log`. Generated records and frozen cohorts remain
untouched.

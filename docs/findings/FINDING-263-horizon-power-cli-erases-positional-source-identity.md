# FINDING-263: Horizon power CLI erases positional source identity

- **Date:** 2026-10-17
- **Severity:** Medium — requested source count and seed can silently change
- **Status:** Resolved by ADR-311 token-position extraction
- **Reviewed source:** `f5c66c97`, backend/scripts/horizon_power_calibration.py

## Evidence

The horizon driver excludes positional strings appearing in a set of option
values. It cannot distinguish independent tokens that happen to have equal text.
The separate AR driver was corrected by ADR-307; its tests do not exercise this
horizon entrypoint.

Independent and parent mock-only public-main calls reproduce:

| Arguments after script name | Requested count / seeds | Observed count / seeds |
|---|---|---|
| `2 7400 --n-bars 7400` | 2 / 7400,7401 | 2 / 0,1 |
| `7400 2 --n-bars 7400` | 7400 / 2..7401 | 2 / 0,1 |
| `2 9 --out 2` | 2 / 9,10 | 9 / 0..8 |
| `2 9 --out 9` | 2 / 9,10 | 2 / 0,1 |
| `2 9 --half-life 2` | 2 / 9,10 | 9 / 0..8 |
| `2 9 --n-bars 7400` | 2 / 9,10 | 2 / 9,10 (preserved) |

Every generator, scorer, measurement, report and output write was mocked. The
7400-count example invoked only two fake generators. No actual source, score,
search, driver output file or frozen cohort was executed or read. The driver prints its
mistaken parsed inputs, so these witnesses do not establish a false persisted
headline, an affected historical measurement or a false graduate.

Receipts: `/tmp/qf-w42-s28-band-cli-review.md` (executable reproduction;
SHA256 `af88957ac5d03a71089ca77579c1d08b18875f86e062a80c20086a4a324f01ac`)
and independent parent `/tmp/qf-w42-s28-band-cli-parent-probe.json`.

## Governed correction

ADR-311 applies token-position extraction for the four known value flags while
preserving first-option lookup, defaults, parsing policy, source/scorer/search
calls, seed arithmetic and output behavior. Repeated options exclude all their
value positions while the first supplies the option. New flags must extend this
registry. This is a command identity fix, not a source-law or scoring correction.

No source/cohort retry, redraw, relabeling, threshold change, v14 update or
artifact rewrite is authorized. F159's residual report wording and prospective
production reference attribution are separate.

Actual pre-runtime RED closed with 11 failed and four preserved cases in
2.15s (`/tmp/qf-w42-s28-horizon-cli-red.log`), all failures at exact source-call
assertions. After the extraction-only change, 34 focused cases passed including
all 15 new cases and existing AR/history controls. Independent required research
review approved all five paths and independently passed the new 15 cases.
Ruff, formatting and mypy passed.

Parent AST comparison allows exactly the three-statement positional extraction
replacement; all original flag/default parsing, source/reference/scoring,
measurement, report and output operations match exactly. Every existing test
remains unchanged. Receipt: `/tmp/qf-w42-s28-horizon-cli-source-audit.json`,
script SHA256
`3edd7e64c4f266df1997afb7e5ceb8a5e33bbfb14cd1544ba710f4376d876bb5`.
The tests mock every scientific call and write only controlled mock output to
fresh pytest scratch paths. Fresh full foreground `make check-all` passed
12,704 backend tests (97.40% coverage) and 401 frontend tests (97.68% statements),
with lint, formatting and strict types green. All local verification is closed;
exact master CI is checked after individual publication.

# FINDING-262: AR power CLI option values silently discard positional count or seed

- **Date:** 2026-10-17
- **Status:** Resolved — ADR-307 implemented and full gate passed
- **Area:** backend/scripts/power_calibration.py main argument extraction

## Reproduction

The driver puts option values into a set and discards every positional token with
equal text. A mocked invocation `2 7400 --n-bars 7400` requests two symbols with
seed 7400, but actually calls the fake generator with seeds 0,1. The seed token is
removed because it matches the history flag value. `7400 2 --n-bars 7400` requests
7400 symbols with seed 2, but executes two fake generations at seeds 0,1. Control
`2 9 --n-bars 7400` correctly uses seeds 9,10.

Parent receipt: `/tmp/qf-w42-s25-cli-positional-probe.json`. All generator,
measure_power and report calls were mocked. There were zero real source draws,
searches, external requests or artifact writes. The printed command summary
reflects the mistaken parsed values; no actual historical false headline or
affected calibration is established.

## Correction and limits

ADR-307 excludes value tokens by their known option positions, preserving equal
text in real positional arguments. Existing first-option lookup, defaults,
positional order, global seed/shard arithmetic, source/reference calls and search
remain. Repeated known option values are all excluded while the first value wins.
Unknown/equal-sign/missing-option policy is not redesigned. Future value options
must join the registry.

No source law, statistic, threshold, fingerprint, accounting-v14, workflow or
generated record changes. Frozen sources/results are not rerun, redrawn or
reinterpreted. The separate F155 reference-method opt-in remains unadopted until
this prerequisite is individually verified and delivered.

Actual TDD produced six failing cases and six passing controls before runtime
edits, in 2.18 seconds (`/tmp/qf-w42-s25-cli-positional-red.log`). Failures assert
exact mocked source count/seed identity for history-value and numeric relative
output-path collisions. Default, shard and first-option controls pass. No real
source generation or search occurred. Focused verification passed 188 tests in
3.27 seconds with three existing serialization warnings. After that run, a
repeated-output preservation case was strengthened by placing both option/value
pairs before positionals; the original RED receipt remains unchanged and is not
retroactively restated. The final 12-case CLI suite passed in 2.02 seconds.

Ruff/format and mypy184 passed. Parent review approves the extraction and tests.
`/tmp/qf-w42-s25-source307.json` confirms only main's positional extraction changed,
with exactly the five known value flags; all other driver AST and all existing
unit tests remain unchanged. Every mock case asserts exact generator calls,
symbol identity and measurement options. Foreground `make check-all` passed: 12,507 backend tests, 97.41% coverage; 381 frontend tests, 97.66% statements. No validation threshold changed.

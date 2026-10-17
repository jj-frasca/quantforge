# FINDING-260: Native holdout floor wrap can expose the entire source to search

- **Date:** 2026-10-17
- **Status:** Resolved — ADR-305
- **Area:** both public holdout splitters' count arithmetic and portion geometry

## Reproduction

For an ordinary finite1000-row ascending unique daily frame, call either
split_holdout(frame,"SYNTHETIC",min_holdout_bars=np.uint64(2**64-1)) or
split_panel_holdout(frame,min_holdout_bars=np.uint64(2**64-1)), leaving every other
argument at its default. Both return1000 search rows and zero holdout rows under
ordinary NumPy policy, with overflow encountered in scalar subtract. The unsigned
floor survives max;1000-floor wraps to1001, passes min_search252, and iloc clamps
the portions. Equal Python-int floor raises the original insufficient-data error;
ordinary unsigned252 gives748/252. Independent and parent probes agree.

On8 ordered rows, fraction.01/min_holdout0/min_search1 separately accepts8/0;
min_holdout8/min_search0 accepts0/8. A negative search floor can permit negative
iloc geometry: requested holdout10 on8 rows with min_search-2 returns6/2.
Boolean, NaN and fractional floors lack an original cardinality boundary.

Scratch report: `/tmp/qf-w42-s25-floor-geometry-finding.md`.
Independent probe: `/tmp/qf-w42-s25-floor-overflow-probe.py` and its JSON receipt.
Parent reproduction: `/tmp/qf-w42-s25-floor-parent-probe.json`.

## Attribution and limits

The positive unsigned example violates ADR-016/024's actual floor geometry without
depending on ambiguous zero-floor semantics. Both search wrappers hardcode safe
default split arguments. No normal-wrapper exploit, production occurrence, actual
catalog lookahead, historical contamination, false graduate or changed rate is
established. These bounded standalone probes performed no search, network access,
generated-data write or frozen-cohort retry. ADR-304 buffer/axis isolation remains
correct and independent.

## Correction and verification

ADR-305 validates original nonnegative nonboolean Integral floors after existing
fraction/calendar checks, normalizes to Python int before arithmetic, retains
the original size refusal, then requires both actual portions nonempty before
copy/slicing. Zero floors with nonempty fractional geometry remain valid. Source
values, split recipe, defaults, estimators, thresholds, fingerprints and v14 stay.

The new public boundary tests first produced 94 failures and 42 preserved cases
in 2.97 seconds before runtime edits: `/tmp/qf-w42-s25-floor-red.log`. Failures
include unsigned wrap across NumPy error policies, malformed original floors,
empty portions, refusal before length access and Hypothesis boundary geometry.
The first focused existing/new suite passed 281 cases in 6.05 seconds, with
three existing timedelta deprecation warnings. After that run, a missing test
return annotation and two explicit ordinary unsigned252 preservation controls
were added without runtime changes. The final new suite passed all 138 cases
in 2.52 seconds. Original RED and initial GREEN logs remain preserved; the two
additional cases are preservation controls, not retroactively claimed RED.

Parent review confirms the intended source boundary and test coverage. Exact
AST audit `/tmp/qf-w42-s25-source305.json` verifies only the two count-normalizing
assignments and one nonempty guard per splitter, their specified precedence,
the new import and named docstrings. All other production AST and all existing
test bytes remain unchanged. Ruff/format and mypy184 passed. The four frozen
standalone scientific payloads from ADR-304 match exactly after this correction
(`/tmp/qf-w42-s25-floor-payload-check.log`); this is bounded regression evidence,
not calibration, universal arithmetic certification or a historical-source retry.

Fresh session25 foreground `make check-all` completed successfully: 12,389
backend tests, 97.41% coverage; 381 frontend tests, 97.66% statements; all Ruff,
format, mypy184, ESLint and TypeScript checks green. Log:
`/tmp/qf-w42-s25-check305.log`. Historical/frozen sources remain untouched;
no inference about their outcomes is licensed.

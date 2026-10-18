# FINDING-268: Parameter stability coerces unsupported original evidence

- **Status:** Resolved — ADR-317 original-evidence and dimensionality guards
- **Date:** 2026-10-18
- **Scope:** Public parameter_stability input boundary

## Reproduction

Before implementation, deterministic direct calls returned stability1 and
fraction_profitable1 for `[True, True]`, two NumPy booleans, `['1.5', '1.5']`,
numeric bytes, `[[1.5], [1.5]]` and a 2x2 all-one ndarray. A native complex
ndarray `[1+5j, 1+7j]` discarded imaginary components with ComplexWarning and
also returned stability1. Python complex lists instead raised TypeError,
making original evidence acceptance container-dependent. A numeric-label 2x2
DataFrame iterates scalar labels but converts to a matrix and likewise produced
perfect stability. These are public-helper witnesses, not strategy outcomes.

The initial length check counts configurations while unqualified array
reductions summarize every cell; a matrix therefore has no scalar-per-config
identity. Float64 conversion also erases booleans and textual/imaginary evidence
before any original-value validation can occur.

Nonfinite and missing observations yield NaN summaries rather than valid
finite stability. Valid finite `[1e308, 1e308]` also yields NaN through native
reduction overflow; that separate arithmetic limitation is not repaired here.

## Impact and correction boundary

ValidationEngine constructs its list from computed backtest Sharpe floats;
cross-sectional search similarly constructs per-configuration Sharpe values.
Report/trial boundaries separately constrain finite scores. No affected
production run, calibration, API exploit or false graduate is established.
The standalone helper still owes an explicit supported-evidence boundary.

ADR-317 retains minimum-count precedence, validates original nonboolean Real
observations with finite binary64 inspection, and requires the converted array
to be one-dimensional before reductions. Decimal and arbitrary coercible
non-Real objects become intentionally unsupported despite prior implicit
conversion. Supported integers, Fraction, NumPy reals, mixed real sequences and
one-dimensional arrays retain all existing numerical operations.

No heuristic, epsilon, sample denominator, clipping, dataclass, report schema,
selector, gate threshold, search identity, accounting-v14 or generated data
changes. Extreme native reduction arithmetic, arbitrary finite rounding,
standalone result construction and hostile conversion code remain separate.

## Evidence and verification

Independent pre-edit review and reproductions:
`/tmp/qf-w42-s33-parameter-stability-review.md`. Twenty valid pre-edit result
payloads were frozen in `/tmp/qf-w42-s33-stability-baseline.json`, SHA256
`d40ce219ec1ea68b562d12da78271081c514b649ea0e3944b2a2ade9576ffbbc`.
Original source SHA256:
`a3648cb8d242a07dd350ee7708f922f6eb9bfdbc61f551d67712305a0bb2f434`.
Independent scope review approved the original-leaf plus converted-shape guard.
The actual preimplementation run observed32 failing cases and13 preserved
controls in3.93s (`/tmp/qf-w42-s33-stability-red.log`); production diff was empty.
After the guards, all45 new cases plus5 original tests passed, including
Hypothesis properties for original-boolean refusal and exact stability of
identical dyadic real observations. The first full gate stopped at mypy before
tests: its float/Real static intersection was unreachable. An object-typed
original-evidence alias, matching the project's existing pattern, fixed typing
without changing numerical operations. The fresh focused50 tests, Ruff and
mypy186 passed after that refinement.

A separate parent audit confirms exact equality of every field in all20 frozen
valid payloads. The entire original module AST is identical after removing
precisely two imports, the new original-evidence loop and dimensional guard,
and restoring the original docstring. Receipt
`/tmp/qf-w42-s33-stability-parent-final-audit.json`, SHA256
`9ec648198ab11bc5fedc9b1513ad362d818c7f7e4cc6efe9035e614df4939738`.
Current source SHA256:
`7962261126739abf1e97e18dbb0e5c342b148d93294dc78d0c3d02cbec30963d`.
The original tests, frontend and generated data retain their bytes.
Independent final five-path research review approved the correction, tests,
ADR and documentation after the typing refinement. Its separate20-baseline and
entire-module AST audit passed again; receipt
`/tmp/qf-w42-s33-stability-final-audit-v2.json`, SHA256
`02894f24dc7f4bc868e5dcba6a807595eb108581240c0f05f3ea622fa2bff4eb`.
Fresh foreground `make check-all PYTEST_WORKERS=4` passed12926 backend tests
(97.39% coverage) and438 frontend tests (97.69% statement coverage), with lint,
formatting and strict typing green. Log `/tmp/qf-w42-s33-check317-final.log`.
All local verification closed before publication; no production source changed
after the reviewed typing refinement.

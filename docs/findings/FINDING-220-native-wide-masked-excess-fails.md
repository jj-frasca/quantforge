# FINDING-220: Native wider and masked numeric excess subtraction fails

- **Status:** Corrected
- **Date:** 2026-10-12
- **Review:** Codex autonomous session 4, ISO 2026-W42
- **Decision:** ADR-271
- **Prior art:** separate mixed nullable limitation disclosed in FINDING-219

## Written finding and mechanism

Three genuine longdouble neighbors of one paired with complete nullable Float64
or Float32 [.01,.02,.03] fail on both sides at excess=strategy-benchmark, before
beta. Installed pandas raises KeyError for float128 when deriving its masked-array
dtype; this is a representation incompatibility despite passing the comparator's
numeric source checks. Signed/unsigned masked integer families reproduce it too.
These failures are distinct from ADR-270's covariance precision defect and were
not silently bundled into that correction.

Independent read-only reproduction found 12 KeyErrors across six masked dtype
families on both sides. A bounded prototype using original native arrays supports
all ten classic Float32/64 and Int/UInt8/16/32/64 dtypes. This public synthetic
failure does not establish historical market contamination or authorize generated
record edits.

## Narrow correction and qualifications

For only classic masked numeric plus genuine native wider sources, construct a
plain native wider excess Series from original aligned np.longdouble arrays.
Preserve aligned index and pandas consensus name through public empty float Series
metadata subtraction. Naive name equality mishandles matching NaN/pd.NA names.
All other pairs retain original subtraction and all original guards/formulas.

No source coercion to float64, filling, clipping, threshold or calibration identity
change. The derived difference uses a supported plain native representation;
source dtypes and observations remain intact. Arrow/Sparse/third-party extension
support is not claimed. Other numerical/source/strict-state limitations remain,
including needed wider beta underflow refusal and separate downstream moments.

## Verification

Independent scratch prototype: 200 complete mixed cases with exact native excess,
Fraction beta, metadata/index/caller-state evidence; 80 complete ordinary/nullable
nonwide baseline outputs unchanged. Missing-value guards and constants preserved.
The pre-code run recorded 41 genuine failures and four preserved aligned-missing
refusals. Only afterward was the bounded subtraction branch implemented. All
214 affected benchmark/API tests pass, with lint/format green. Independent final
review approved 185 targeted tests and 200 actual public mixed comparisons with
exact excess/Fraction beta/name/index/state/input ownership. Eighty complete
nonwide ordinary/nullable and 60 native wider/native comparisons match the
published baseline exactly. Production AST outside the bounded dtype tuple,
excess branch and predicate relocation restores exactly. The complete foreground
gate passed: `make check-all PYTEST_WORKERS=4` completed with 5,664 backend
tests and 363 frontend tests, backend coverage 97.72% and frontend statement
coverage 97.63%; all lint/type/format checks green. Exact master CI is checked
after individual delivery.

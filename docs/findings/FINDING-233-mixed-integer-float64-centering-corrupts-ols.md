# FINDING-233: Mixed integer/Float64 centering corrupts OLS coefficients

- **Status:** Corrected by ADR-284
- **Date:** 2026-10-13
- **Scope:** BenchmarkComparator, supported original integer paired with Float64
- **Prior art:** Remaining mixed-family coverage of FINDING-232/ADR-283

## Reproduction

Benchmark2**60+arange(4)*256 and strategybenchmark+256 still yield accepted
beta0.6666666666666666/annualalpha9.684540638697531e19 when one original source
is native/classic integer64 and the other native/classic Float64. Eight ordered
signed/unsigned64 examples reproduce; centered exact Fraction gives1/64512.
ADR-283 correctly leaves these mixed original dtypes outside its both-Float64
scope, and ADR-275/276 only cover both-integer pairs. Original integer neighbors
can also disappear when covariance extracts floats, independently of centering.
No contamination of historical market records or gate decisions is established.

## Proposed correction and limits

ADR-284 extends the same exact common-grid sufficient sums to supported mixed
integer/Float64 pairs using exact integer ratio(int(value),1), never float
conversion. Prior both-integer/both-Float64 and outside source families remain;
original excess/IR/TE/drawdown are separate unchanged evidence. Coefficient
rounding intentionally changes family-wide; final unrepresentable claims refuse
and valid rounded zero/subnormal coefficients remain. Already-rounded mixed
excess and other statistics are not certified by exact source coefficients.

## Evidence

Independent scratch scope APPROVE:352finite/32overflow helper probes,
288public Fraction pairs,420complete outside-family baselines,64fullwidth/tiny/
rounding controls;100kUInt64/Float64 .24s. Original NumPy integer iterators need
exact int conversion, since they lack as_integer_ratio; Float64 ratio operations
stay unchanged. ADR284 adopted after prior283 exactCI/hooksGREEN andfreshsyncunchanged.
Independent scratch test210casesGREEN beforeadoption. Public tests compare
centeredFraction coefficients and originalexcess/ownership/state directly;
complete other-output and outside-family preservation requires independent
published-baseline final review, avoiding a runtime self-comparison as evidence.
Final repository precode RED172failed/38preserved beforeproduction; then
initial focused16old-dispatch failures/2097passed identified prior283 integer/64
bypass cases intentionally admitted by284. Retained all32parameter cases:
16mixed now require exacthelpercalledonce/beta1alpha0;16outside stillbypass.
Isolated published283baseline16genuineRED/16preserved; final2113focusedGREEN.
No cases/tests removed/skipped, thresholds/domains/tolerances unchanged.

Final independent six-path production review APPROVE:352finite Fractionhelper
pairs/32overflow refusals,288public exact coefficients with accepted283baseline
noncoefficient outputs unchanged,420complete outside-family outputs/refusals
includingbothinteger/both64,64additionalfullwidth/tiny/rounding controls,
eightguardprecedence probes,401new+prior283testsGREEN. Removing only integer
ratio adapter and added eligibility restores baseline moduleAST exactly;
coefficient arithmetic remains unchanged. All independent verification terminal.
Final foreground make check-all PYTEST_WORKERS=4 passed:10553backend tests,
97.64%coverage;363frontend tests,97.63%statements;lint/format/mypy GREEN.
No generated records, validation thresholds or accounting identity changed.

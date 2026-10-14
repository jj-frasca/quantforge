# FINDING-234: Mixed narrow/Float64 source means and centering corrupt OLS

- **Status:** Corrected by ADR-285
- **Date:** 2026-10-13
- **Scope:** Original nativefloat16/32 orclassicFloat32 paired with Float64
- **Prior art:** Remaining mixed-floating coverage of FINDING-232/ADR-283

## Reproduction

Four Float16base2**10+arange4*originalULP observations paired with Float64
original-values plus/minus.5 yield publicalpha252.0000000000573 or0 against
exactannual126. Float32/classicFloat32base2**60 plus four originalULPs with
Float64halfULP counterparts yields publicalpha64512 or34634616274944 vs
exact17317308137472. These six outcomes are finite and accepted.

ClassicFloat32strategy2**60+arange4*2**37 versus Float64benchmark
2**60+arange4*256 publishes beta447392426.6666666 and
alpha-1.299837038344287e29; centeredFraction givesbeta536870912 and
alpha-1.559804446594217e29. Both matched source coefficients must be corrected.
No contamination of historical market records or gate decisions is established.

Initial Float16base2**14 fixture was declined on nonfinite statistics, not
accepted false evidence; it was dismissed before adopting a finding. Actual
accepted fixtures and literal outputs are /tmp/qf-w42-s9-mixed-floating-ols-finding.py.

## Proposed correction and limits

ADR-285 extends exact common-grid coupled coefficients to this mixed original
floating family, leaving helper arithmetic and all prior family outputs intact.
Original narrow values have exact binary ratios; no source conversion is needed.
Only eligibility changes. Existing mixed excess/risk/drawdown and their rounding/
measurability limits remain separate; extreme helper success does not establish
whole-comparator availability. Final coefficient overflow still refuses and true
rounded zero/subnormal remains valid. No threshold or generated record changes.

## Evidence

Independent scratch scope APPROVE:408public Fraction/noncoefficient exact
baseline pairs,90finite/sixoverflow helper controls,472complete outside baselines;
100kFloat32/Float64 .26s. Scratch132tests passed with repositoryRuff config.
Adopted ADR285/tests after archive-rule exactCI/hooksGREEN andfreshsyncunchanged.
Publicnew+predecessor precode RED72failed/461preserved beforeproduction;
all prior32+5case parameter lists retained with explicit new narrow/64 routing.
Implementation changes only eligibility and helperdocstring; final533focused
tests,181mypy modules andRuff GREEN. No test/domain/tolerance/threshold weakened.

Final independent seven-path production review APPROVE:408public Fraction pairs
with exact published1c998f15 noncoefficient/state outputs;90finite/sixoverflow
helper controls;474complete outside-family outputs/refusals includingSparse and
bothpredecessor families;36signedzero/subnormal/overflow controls;8guard probes;
533new+predecessor testsGREEN. Removing only eligibility/helperdocstring changes
restores baseline moduleAST exactly, proving coefficient arithmetic unchanged.
All independent verification terminal. Final foreground make check-all
PYTEST_WORKERS=4 passed:10685backend tests,97.52%coverage;363frontend tests,
97.63%statements;lint/format/mypy GREEN. No generated evidence, accounting
identity or validation threshold changed.

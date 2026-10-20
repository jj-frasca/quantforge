# FINDING-278: NumPy integer lookbacks disappear from the embargo proxy

- **Date:** 2026-10-20
- **Status:** Resolved by ADR-331
- **Scope:** lookback_embargo original integer-parameter predicate

## Reproduction and evidence

Construct 300 daily prices as 100*cumprod(1+default_rng(0).normal(.0002,.01,300)),
starting 2024-01-01 UTC. Validate two SMAStrategy configurations (3,50) and (5,60)
with the ordinary ValidationEngine. Native Python int parameters yield embargo 60
and purged mean -1.9638727674723626. Change only their scalar constructors to
np.int64: signals are exactly identical, but embargo becomes2 and mean becomes
-1.8061046186135523. Both actual reports retain 5 folds and JSON-roundtrip through
ValidationReport. Parent and independent fresh probes reproduce these values.

The helper filters with isinstance(value,int), excluding np.int64 despite its
numbers.Integral identity. ADR-198 correctly checks the smaller declared embargo
but cannot reconstruct the omitted strategy lookback. Unlike FINDING-277's
overlapping-row splitter bug, this case produces an accepted scored report.
An initial uint64 producer probe fails pandas rolling with a buffer dtype error;
it does not establish an accepted unsigned producer result.

## Scope and qualifications

This is a proxy-type omission, not proof of a production leak, affected graduate,
changed rate or universal feature-support horizon. The largest integer parameter
is still only a proxy; FINDING-272's numerical-history limit remains. Purged CV
intentionally selects on future training observations and is diagnostic only.

Longitudinal search and calibration do call this helper through ValidationEngine.
Independent no-search inventory checked 34 catalog entries' coarse and default-
centered refined grids: 1,360 configs, 2,780 int / 1,470 float parameter leaves, no omitted
NumPy integers, and identical old/proposed embargo values. Parent froze 204 helper
payloads across those 68 grids and floor 0/2/10**100, SHA256
f56ee011868facb4733e9a43396915adfdab60213f4fe00f9b170e0de2a48828.
This bounded inventory supplements source-level type reasoning; it is not a
calibration search or proof about arbitrary custom grids/refinement centers.

## Resolution

ADR-331 includes original nonboolean Integral parameters, converting accepted
leaves to Python int before the unchanged maximum. Other parameter types and
floor semantics remain. No historical record, frozen source, generated JSON or
threshold is changed.

Observed preimplementation RED: 18 failed/9 preserved controls before runtime
edits. Final new/old helper and purged suites: 140 passed, including complete
native-int/int64 report equality and JSON roundtrip. Independent five-path
review approved after rerunning 140 tests, 1,200 exact mixed legacy helper
controls and whole prior AST preservation. Parent preserved all 204 frozen
catalog/floor payloads and the prior module AST except the two list expressions
and helper docstring. Foreground make check-all passed 13,399 backend and 566
frontend tests with lint, formatting and types green. Runtime SHA256:
c024774a675675d2ad4999d0e85d82e353814fe3826be13f6a01180e39ee4664.

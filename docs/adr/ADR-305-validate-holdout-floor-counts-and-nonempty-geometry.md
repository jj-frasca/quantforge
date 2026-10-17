# ADR-305: Validate original holdout floors and require nonempty split portions

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** Codex autonomous session25, ISO2026-W42
- **Resolves:** FINDING-260
- **Extends:** ADR-016/024/295/302/304

## Context

Both public splitters accept a positive NumPy uint64 maximum as min_holdout_bars.
On1000 ordered source rows, native subtraction wraps search_n to1001, pandas
clamps the slices, and all1000 rows reach search with an empty holdout. Equal
Python-int input correctly refuses. Default search wrappers use fixed safe floors;
no production occurrence, actual lookahead, false graduate or cohort effect is
established. Zero or malformed floors can separately produce empty or negative
slice geometry; calendar and buffer isolation do not establish valid counts.

## Options considered

1. Validate and normalize original floor counts, then refuse empty geometry.
   This preserves usable zero floors and the existing fraction/floor recipe.
2. Require positive floors universally. This needlessly excludes floor0 when
   the fractional split already produces nonempty portions.
3. Clamp computed counts or cast malformed values. This silently changes the
   requested split or reinterprets invalid original count evidence.
4. Guard search wrappers only. Their defaults are already safe, while the public
   splitters retain the independently demonstrated defect.

## Decision

After the existing fraction and whole-calendar guards, validate min_holdout_bars
then min_search_bars as original nonnegative nonboolean Integral values. Reuse
research.trial_counts.require_trial_count with minimum0 and explicit parameter
names; it is a dependency-free research primitive. Normalize accepted values to
Python int before len, subtraction, comparison or slicing. No shared-helper edit
or broad count refactor is needed.

Preserve holdout_n=max(int(holdout_fraction*n),min_holdout_bars), search_n=n-holdout_n
and the original insufficient-search condition/message exactly. After that original
size refusal, reject either computed portion below1 with an explicit nonempty-
portions error, before copying/slicing. This preserves old positive-floor size
precedence; floor0 remains supported when actual geometry is nonempty. Python
builtin len already returns int and needs no conversion.

No source sorting, clamping, truncation repair, fraction rounding, scoring,
default, threshold, configuration hash, accounting-v14, generated record or
frozen-cohort change. This establishes intrinsic split cardinality, not arbitrary
strategy causality, daily cadence, provenance or hostile-code isolation. Existing
numeric/axis ownership from ADR-304 remains intact. No historical source is rerun
or relabeled and no calibration claim is made.

## Verification and reversal

Observe RED for uint64max versus equal Python-int refusal, invalid original floor
types/counts, and both empty portions before implementation. Cover ignore/warn/raise
NumPy policies without overflow warnings, ordinary native-integral exact geometry,
zero floors, fraction/calendar/floor/size precedence and refusal before length,
copy or slice work. Hypothesis covers reconstruction, nonempty geometry and exact
Python/NumPy floor equivalence across valid and refused boundaries. Keep existing
tests; independently compare the four standalone regression payloads from ADR-304,
review source scope and run foreground make check-all before individual delivery.

Remove only floor validation/normalization and the new nonempty guard to reverse,
reopening FINDING-260. Do not modify generated evidence or validation thresholds.

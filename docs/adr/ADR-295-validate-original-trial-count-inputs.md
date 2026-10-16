# ADR-295: Validate original trial-count inputs before arithmetic

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 19, ISO 2026-W42
- **Resolves:** FINDING-249
- **Extends:** ADR-015/016/024/046
- **Relates to:** ADR-160/190

## Context

The public MinBTL primitive checks only n_trials<1. It accepts boolean and fractional counts, including True/1.0 with zero selection penalty. GraduationGate propagates that result for a manually valid report; an actual production false graduate is not established.

Both public search entry points add original prior_trials directly to the current concrete-config count. A negative integral prior can therefore cancel evaluated hypotheses while leaving a positive lifetime that passes ADR-190's shared DSR guard. Two bounded manual longitudinal calls evaluate the same four configurations: prior0 returns lifetime4 and a positive DSR penalty; prior−3 returns lifetime1, zero penalty and zero MinTRL requirement. Both Experiment records roundtrip. Cross-sectional source uses the same addition/repricing/gate pattern. No panel search, real/provider data, persisted outcomes or calibration is involved.

Valid cumulative counts are discrete nonnegative counts, not caller-coercible numeric estimates. Validating only after addition also loses original boolean/type evidence and permits NumPy fixed-width overflow before the guard.

## Decision

Add one small `backend/app/research/trial_counts.py` helper owning original nonboolean numbers.Integral validation, permitted lower bound (0 or1), ValueError and normalization to Python int. It performs no statistical calculation. NumPy integral scalars remain accepted through numbers.Integral; NumPy booleans/0-D arrays do not. Do not coerce floats, Fractions, strings, arrays or booleans into counts.

`minbtl_years` requires original n_trials>=1 through this helper before its nonpositive-Sharpe shortcut and unchanged formula. GraduationGate inherits the same guard through the public primitive; its report reconstruction order remains unchanged.

`run_search` and `run_cross_sectional_search` require original prior_trials>=0 at entry, before holdout splitting, registry/frame access, candidate evaluation or addition. Use the normalized Python integer for lifetime arithmetic. This prevents fixed-width scalar wrap before addition. Reuse one helper rather than duplicating count-domain rules. Existing expected_max_sharpe validation remains untouched.

Valid Python-integer inputs retain exact existing arithmetic, gates, grids, selection rules and thresholds. Calibration uses prior0; its procedure and v14 accounting/search identity remain unchanged. Accepted NumPy integral priors are now added as mathematical Python integers: previous scalar wrap or unsafe promotion is deliberately removed. Do not claim bit-for-bit preservation of those formerly defective boundary executions.

Leave Experiment/CrossSectionalExperiment persistence schemas, historical counters, generated files and frozen cohorts untouched. No retrospective claim about stored undercount, production false graduates, rates or calibration is established. Sharpe overflow/underflow, NaN or track-record/config guards are outside scope.

## Alternatives

1. Validate resulting lifetime only: cannot recover canceled hypotheses or original type evidence.
2. Clamp/round negative or fractional priors: invents accounting and preserves ambiguity.
3. Harden persisted historical counters concurrently: broadens compatibility scope and risks relabeling historical lower-bound evidence.
4. Reject all non-Python ints: unnecessarily excludes supported NumPy integer scalars; normalize them instead.

## Verification and reversal

TDD public MinBTL/GraduationGate malformed-count refusal, both public searches rejecting malformed original priors before any work, and valid zero/cumulative/NumPy boundaries. Include signed/unsigned NumPy integral maxima normalized before addition, original boolean/fraction/float/string/list/zero-D-array rejection, negative count and nonpositive-Sharpe shortcut precedence. Financial Hypothesis properties verify ordinary bounded-Sharpe MinBTL monotonicity in trial count and inverse-square scaling in positive Sharpe. Existing valid search/accounting/fingerprint regressions remain green. Independent review, foreground make check-all and exact master CI are required.

Remove the helper and restore original weak guards/addition to reverse. Preserve the finding and manual receipts; that reopens the original input-boundary defect.

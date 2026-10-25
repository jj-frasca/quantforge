# ADR-370: Normalize longitudinal momentum counts before shift arithmetic

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Codex autonomous session32, ISO2026-W43
- **Resolves:** FINDING-311
- **Extends:** ADR-007/295/314 (same discrete-count guard, separate constructor)

## Context

MomentumStrategy retains positive fixed-width NumPy lookback and skip values.
Their addition can wrap into a negative reference shift, making earlier signals
and actual default-cost engine returns depend on future prices. Unsigned wrap
can also substitute a different trailing window. F311's parent and independent
synthetic public-engine witnesses establish both boundaries, without an affected
production/default/API/catalog result or false-graduate claim.

## Decision

Import existing require_trial_count in momentum.py. At constructor entry, replace
its two bound checks with lookback=require_trial_count(lookback,minimum=1,
parameter="lookback") and skip=require_trial_count(skip,minimum=0,parameter="skip"),
then retain the existing self assignments. Original operands must be nonboolean
Integral scalars. Normalize to Python int before storage, so reference period
addition uses mathematical integer arithmetic. Reject float, Fraction, boolean,
array and other coercible inputs rather than silently truncating their values.

Keep signature/defaults, positive-lookback/nonnegative-skip meanings and parameter
names in ValueErrors. Exact error wording changes to the shared helper's message;
no promise of the old literal wording is retained. Preserve parameters property,
signal formulas, warmup, return lag, turnover costs, all other strategies,
API/grid/factory policies, validation thresholds and accounting-v14. Default
coarse and refined search fingerprints must remain exact. No generated-file or
frozen-cohort changes or calibration/source searches are required.

Normalization intentionally changes accepted NumPy stored scalar types. This
is not constructor immutability or revalidation after caller attribute writes.
Huge Python counts may still refuse in pandas; this decision promises no
arbitrary-sized pandas shift. Source arithmetic and caller NumPy error policy
remain unchanged after counts have been safely normalized.

## Alternatives and tradeoffs

- Cast only the final sum: too late; original fixed-width addition already wraps.
- Cast blindly with int: truncates fractional inputs into another strategy.
- Ban NumPy integral counts: needless rejection when exact Python normalization
  can preserve their mathematical values.
- Normalize in generate_signals only: leaves reconstruction parameters with
  native overflow behavior; constructor storage is the narrow authoritative point.
- Broaden to all strategy counts or freeze attributes: separate contracts without
  this demonstrated summed-shift defect; outside this targeted correction.

## Verification and reversal

Observe RED first for signed/unsigned wrap and constructor count domains.
Hypothesis verifies signal and actual net-return prefix invariance under future
perturbations with formerly wrapping counts. Test all NumPy error policies,
zero skip, negative bounds, large integral normalization and safe NumPy/Python
controls. Replay96 prepatch complete signal/engine payloads and whole-module AST
except exactly the new import and constructor replacement. Verify both default
fingerprints, independent final review, foreground make check-all, individual
push and exact CI. No current production occurrence is inferred from these tests.

Restore the two bound checks and remove the helper import to reverse, reopening
F311. Preserve original evidence, generated files and all frozen sources.

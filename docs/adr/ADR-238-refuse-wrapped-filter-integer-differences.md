# ADR-238: Refuse wrapped band-filter integer differences

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 31, ISO 2026-W41
- **Resolves:** FINDING-188
- **Extends:** ADR-061, ADR-234, ADR-236

## Context

Original finite integer log observations can produce wrapped native differences.
Unsigned decreases become large positive innovations; signed overflow becomes a
small innovation with the opposite sign. All subsequent quantities can remain
finite, so finite arithmetic guards do not establish native integer measurability.

## Options Considered

1. Refuse exact adjacent differences outside the original integer dtype's range.
   Narrow and preserves measurable native arithmetic; rejects wrapped callers.
2. Convert integer observations to float before differencing. Avoids some wrapping,
   but loses valid adjacent uint64 observations differing by one; rejected.
3. Trust finite outputs. Misses wrapped innovations and false state estimates.

## Decision

After existing parameter/source guards, and before filter arithmetic, inspect
integer sources using exact Python integer subtraction of adjacent original
observations. Require every difference within the original signed/unsigned dtype's
np.iinfo range. Raise ValueError for unrepresentable native integer differences.
Keep the original source in np.diff and all state operations for accepted inputs.
Do not normalize dtypes, rewrite differences, clip or fabricate innovations.

Preserve floating sources, valid signed decreases, nondecreasing unsigned sources,
empty/singleton histories, all-false masks, byte order and input ownership. Keep
uint64[max-1,max] measurable with its original difference one, despite float64
observation projection losing that difference. This is native integer subtraction
measurability, not a general precision or conditioning guarantee. Initialization,
reference meanings, defaults, thresholds, fingerprints and artifacts stay fixed.
FINDING-155 and FINDING-159 remain Open.

## Verification

Before implementation test unsigned decreases and signed overflow in both
directions across integer widths and NumPy error policies. Preserve native valid
integer differences, adjacent large uint64 values, masks, short histories and
parameter/source precedence. Include property-based unsigned-decrease refusal.
Independent review compares exact native outputs, producers and reference scores.
Full foreground make check-all and exact master CI precede completion.

## Consequences and reversal

Wrapped finite innovations cannot obtain band-state evidence. Remove the exact
integer preflight to reverse this decision and reopen FINDING-188; no historical
source or experiment is restated.

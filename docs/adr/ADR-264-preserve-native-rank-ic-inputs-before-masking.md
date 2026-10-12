# ADR-264: Preserve native rank-IC inputs before masking

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 3, ISO 2026-W42
- **Resolves:** FINDING-213
- **Extends:** ADR-035
- **Relates to:** ADR-261, ADR-262

## Context

rank_ic masks pairwise unscorable names before average ranking. Masking native
integer columns with the final unavailable forward return inserts NaN and first
narrows them to float64; even homogeneous int64 scores lose represented order.
Wide numeric ranking separately narrows native scores/forward returns to float64.
Fabricated average ties publish IC approximately 0.866 where represented native
ordering requires approximately 1. Ordinary production float64 generators do not
exercise these paths; this is a supported direct-input diagnostic correction.

## Options Considered

1. Preserve native scalars before masking on each ranked side.
   - Pro: retains average ties, pairwise missingness and the existing vectorized
     rank/correlation computation, with narrow dtype-based selection.
   - Con: object ranking costs more for native integer/wide-input panels.
2. Convert after masking or reuse the portfolio ranker directly.
   - Pro: superficially shares ranking machinery.
   - Con: masking has already lost integers; portfolio first ties and allocations
     do not implement average-tie Spearman correlation.
3. Replace all IC ranks with row-wise exact sorting or reject native inputs.
   - Pro: explicit represented-order control or fail-closed evidence.
   - Con: larger implementation/performance change or drops valid supported input.

## Decision

Use a private average-rank helper on each original frame plus the existing scorable
mask. If any column has a native NumPy signed/unsigned integer dtype or floating
dtype wider than float64, convert the original frame to object before where(mask),
retaining represented integer/wide scalars. Otherwise use the original frame.
Then execute the unchanged where(mask).rank(axis=1) average-tie operation. Apply
separately to original signals and forward asset returns; do not recover scores
already rounded by their producer or constructor.

Retain ordered-column matching, checked native asset returns, forward shift,
pairwise NaN exclusion, minimum ranked names, undefined-date dropping, centered
rank/norm/correlation arithmetic, return name, summary formulas and caller state.
Ordinary float64/float32, nullable/object/bool paths remain unchanged. No dtype ban,
new infinity/source-domain/summary/calendar policy, clipping, estimator or gate
threshold change is bundled with this correction.

## Consequences, identity and reversal

Finite direct native IC observations change where masking or ranking fabricated
ties. This diagnostic neither gates, selects nor sizes; its optimistic independent-
period t-statistic and in-sample nature remain qualified by ADR-035. Canonical
float64 prices and all 16 generators/45 configurations retain exact IC results
in independent comparison. Longitudinal calibrated search does not use this IC
module; accounting identity and generated historical evidence stay unchanged.
No historical production contamination or universal precision guarantee is inferred.
Separate infinity and summary-domain findings remain independent.

Observe native-input RED before code, including homogeneous integers masked by the
last forward date, mixed scores, wide forward returns, true average ties, pairwise
missingness and degenerate/empty panels. Verify an exact rational average-rank
oracle, strict NumPy state, caller nonmutation, ordinary exact baselines and all
standard generators with independent review and foreground make check-all.
Deliver individually and watch exact CI. Remove the helper and restore the two
original where/rank expressions to reverse this correction and reopen FINDING-213.

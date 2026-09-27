# FINDING-071: Cross-sectional forward testing mutates the frozen universe

- **Severity:** High — one vendor failure changes the factor, benchmark, and durable forward claim
- **Status:** Resolved by ADR-140
- **Date:** 2026-09-27
- **Affects:** cross-sectional forward acquisition, scoring, lifecycle, and book evidence

## Finding

ADR-025 freezes a cross-sectional graduate's universe because the signal is defined by ranks across
that exact set and its benchmark is the same universe held equal-weight. The production forward
driver catches each fresh vendor failure and silently omits that symbol before panel construction.
`manage_cross_sectional_book` accepts the resulting plain panel without comparing its columns to
`CrossSectionalPosition.universe_symbols`.

A transient failure therefore creates a different strategy: every remaining rank and long/short
leg can change, as can the equal-weight benchmark. The new score overwrites the prior durable score
under the original frozen universe label. The fresh frames also bypass `DataQualityEngine`, and the
score stores no per-symbol report/source/range/revision identity, so the altered claim cannot be
reconstructed.

## Required correction

Require the panel provider to return one quality-checked `ResearchDataset` for every frozen symbol.
Validate exact symbol membership, report-symbol agreement, a single executed revision, and the
post-alignment panel columns before scoring. Any fetch, quality, history, or identity failure must
leave that position unchanged for the cycle rather than narrowing its universe. Persist the ordered
dataset evidence for every component beside each new forward score; legacy and synthetic scores may
retain absent evidence.

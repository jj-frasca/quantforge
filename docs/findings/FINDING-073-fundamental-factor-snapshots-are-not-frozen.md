# FINDING-073: Fundamental factor snapshots are not frozen with cross-sectional claims

- **Severity:** High — a graduated factor cannot be reproduced or forward-tested as selected
- **Status:** Resolved by ADR-142
- **Date:** 2026-09-27
- **Affects:** cross-sectional discovery lineage, promotion, and forward lifecycle

## Finding

The production cross-sectional hunt supplies static value and quality score maps from the weekly
fundamentals pool. Those maps define every return in `xs_value`, `xs_quality`, and
`xs_quality_value`, yet `CrossSectionalExperiment` persists neither snapshot. The durable trial,
graduate, and panel manifest therefore do not contain enough input to reconstruct a fundamental
factor claim after the fundamentals pool changes.

The forward path compounds the defect. `CrossSectionalPosition` can hold only an optional value map,
promotion accepts one caller-supplied live value map for every experiment, and the production driver
supplies none. There is no quality map at all. Consequently a newly promoted fundamental graduate is
absent from the rebuilt registry; scoring raises `ValueError` outside the provider fail-soft block
and can abort the entire book update. Supplying today's pool would avoid the exception but silently
forward-test a different frozen factor.

## Required correction

Project the exact value and quality mappings used by a search onto the retained panel and persist
both snapshots on every new experiment. Promotion must copy only those historical experiment
snapshots into the position; callers must not substitute current fundamentals. Rebuild the forward
registry from both frozen maps so all three fundamental strategies retain their selected identity.
Legacy fundamental graduates without snapshots must remain readable but be skipped at promotion
because their claim cannot be reconstructed honestly.

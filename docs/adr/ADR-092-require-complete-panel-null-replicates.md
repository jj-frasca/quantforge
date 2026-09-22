# ADR-092: Require complete symbol cohorts in every panel-null replicate

- **Status:** Accepted
- **Date:** 2026-09-21
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-028
- **Extends:** ADR-081, ADR-085, ADR-087

## Context

ADR-085 makes the observed panel statistic one production search per symbol on the complete frozen
source cohort and aborts preparation if any symbol fails. ADR-081's null execution instead permits
each generated panel to retain only `min_successful_symbols`, currently the 30-symbol reporting
floor inherited from ADR-067, and computes the median over that successful subset.

The current 39-symbol cohort could therefore yield null medians over different, data-dependent
subsets. A minimum sample size protects precision but not estimand identity. Exact panel-level tail
inference requires all 400 replicates to apply the same equal-symbol function as the observed arm.

## Options considered

1. **Keep the 30-symbol floor and expose each error list.**
   - Pro: tolerates isolated search failures and makes a long measurement more likely to finish.
   - Con: auditable missingness is still data-dependent missingness; replicate medians no longer
     measure one fixed statistic.
2. **Impute a failed symbol's excess diagnostic.**
   - Pro: preserves a constant symbol count.
   - Con: no pre-registered, evidence-backed imputation value exists, and choosing one after a
     generated failure would add a new methodology assumption.
3. **Require complete success in every observed and null panel.**
   - Pro: preserves the exact frozen equal-symbol estimand and makes any execution failure loud.
   - Con: one symbol failure invalidates its batch and, under ADR-087, requires a full pre-result
     rerun rather than partial publication.

## Decision

Choose option 3. `PanelNullCohort.min_successful_symbols` remains a serialized identity field but
must equal the complete frozen cohort size. Production binding derives it from `len(symbols)`, not
from the eligibility floor. Whole-panel execution still attempts every symbol and retains their
messages while running, but if any search fails it raises one aggregated error and emits no
replicate. Direct cohort, shard, and final-artifact construction reject a lower completeness floor.

ADR-087's stage rule remains: because no consolidated inference exists, a failure requires a full
workflow rerun. No panel index, seed, generator, diagnostic, inference input, gate, or validation
threshold changes.

## Consequences

- Every accepted null replicate applies the same symbol-complete median as the observed panel.
- Tail counts remain 400 independent applications of one frozen statistic rather than a mixture of
  subset-specific statistics.
- Transient symbol failures are more operationally expensive, but cannot silently change the
  scientific claim to keep a run green.
- The measurement remains unspent, so no legacy compatibility or generated-data migration exists.

## Reversal

Allowing partial panels again requires a new pre-stated missing-data estimand and fresh inference
design. Restoring the 30-symbol execution floor without that decision restores FINDING-028.

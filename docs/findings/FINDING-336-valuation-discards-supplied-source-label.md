# FINDING-336: Valuation discards the supplied history source label

- **Status:** Corrected for new producer output by ADR-400; historical labels remain unknown
- **Date:** 2026-10-28, Codex autonomous session14 (ISO2026-W44)
- **Producing revision:** 7404dc5b
- **Affected:** score_valuation and its injected value-provider composition
- **Related:** FINDING-335; ADR-022/023/373/399

## Evidence

Three validated histories with identical rows and filing metadata but source
"SEC EDGAR", "Synthetic supplied source" and "" produce identical complete
valuation JSON labelled "SEC EDGAR". score_valuation copies entity/form/accession/
URL but omits source from its final constructor, selecting the public model's
default instead. The real make_value_provider composition also returns the
default after calling injected history and price providers. Independent research
and data reviews reproduce this without services. ADR-399's new record citation
retains the actual label, exposing the separate valuation-label inconsistency.

This is a constructed accepted-input attribution defect, not source authentication
or a measured production occurrence. Ordinary SEC EDGAR histories already agree
with the default. No incorrect numeric score, graduate, trading effect, provider
incidence or changed calibration rate is established. Historical stored labels
cannot reveal whether the source was supplied or silently defaulted.

## Bounded correction

ADR-400 adds only source=history.source to the final producer constructor. Every
ordinary validated string, including empty strings, is retained exactly; no
normalization, URL/source whitelist, fetch, authentication or fallback is added.
Keep the public model default and existing serialized records unchanged. The
new label identifies supplied history metadata, not fact ownership, physical
periods, availability/PIT, source authenticity or price/code provenance.

Earlier arithmetic and explicit refusals still run before final construction.
Newly consumed malformed unchecked source values can now fail existing final
string validation, including alongside other output-validation errors. This is
an explicit availability restriction; final error ordering and all caller
exceptions are not claimed unchanged. Provider scoring stays outside acquisition
fallback; hunt per-symbol error handling remains. No skip/recovery is added.
No numeric formula, score, flag, schema/default, threshold, fingerprint, v14,
generated-record repair or search/cohort change occurs.

## Verification

Before source edits, 290 complete ordinary valuation JSON/Python claims, the
schema and whole score-module AST were frozen. The actual precode run produced
19 expected failures and 6 passing controls; the 25-test suite includes a string
roundtrip Hypothesis property. Initial focused verification passed 144 tests.
Session16 resumed the seven owned paths before synchronization and independently
replayed all 290 claims/schema/AST exactly outside the sole added keyword.

Final independent research review approved with 133 synthetic tests passing and
1 live test deselected. Data review approved with separate 52-test (1 live test
deselected) and 194-test synthetic selections plus 6 supplemental controls for
validated histories, existing string coercion and simultaneous metadata errors.
All checks used offline dependencies and excluded live/integration tests.

The foreground full-gate and exact publication CI receipts are recorded separately
in the session ledger. This evidence establishes the bounded producer correction;
it adds no historical reconstruction, source authentication or incidence claim.

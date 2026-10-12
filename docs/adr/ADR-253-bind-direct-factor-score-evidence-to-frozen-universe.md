# ADR-253: Bind direct factor score evidence to frozen universe

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 35, ISO 2026-W41
- **Resolves:** FINDING-202
- **Extends:** ADR-140, ADR-149, ADR-164, ADR-252

## Context

ADR-252 binds the raw price panel to the frozen position, but optional supplied
score evidence can still name a partial, substituted or reordered universe.
Standalone score validation enforces evidence leaf validity and one revision,
while only complete position attachment checks ordered symbols against the target.
A direct score can therefore publish contradictory evidence before attachment.

## Options Considered

1. Revalidate supplied evidence leaves and bind their ordered symbols at entry.
   - Pro: reuses native leaf rules and the existing position identity relationship.
   - Con: reconstructs supplied evidence before the output model reconstructs it.
2. Rely on eventual complete position attachment.
   - Pro: no scorer change.
   - Con: direct standalone scores still publish wrong universe evidence.
3. Require evidence on all direct calls or invent missing components.
   - Pro: every score would have a nominal component list.
   - Con: breaks deliberate evidence-null synthetic calls or fabricates provenance.

## Decision

After the existing exact panel-column check and before calendar/scoring work,
reconstruct each present ResearchDatasetEvidence through its authoritative model.
Use round-trip dumps for model instances and retain the already accepted raw
dictionary form. Require normalized ordered report symbols to equal normalized
frozen universe symbols, using the complete position's existing strip/uppercase
comparison. Refuse mismatch with ValueError; preserve None without invented evidence.

The output model retains its existing revision, nested evidence and statistic
validation. No new source/evidence policy, price/calendar rule, position validation,
factor, estimator, threshold, schema, broker action or generated record changes.

## Consequences and reversal

Direct score evidence names the same frozen ranked universe as its prices and
target. Existing valid model/raw-dictionary inputs and evidence-null synthetic
calls keep their exact results. Supplied evidence pays one early reconstruction;
invalid copies and wrong membership/order refuse before compute. Remove the entry
evidence block to reverse this correction and reopen FINDING-202.

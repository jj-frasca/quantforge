# ADR-382: Require finite DCF assumption values at construction

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session5, ISO2026-W44
- **Resolves:** FINDING-325 for ordinary validated configuration
- **Extends:** ADR-022; distinct from ADR-372/373 and ADR-381

## Context

DcfAssumptions accepts nonfinite floating configuration. NaN growth bounds can
silently disable native clamping while the actual DCF and valuation output stays
finite. The output guard in ADR-373 cannot detect malformed configuration lost
before output construction. Assumptions JSON changes NaN to null and cannot
revalidate that nonnullable field. Independent data/research and parent synthetic
probes confirm the defect; no affected production run is established.

## Options Considered

1. **Require finite values in the shared assumption model (chosen).** Ordinary
   constructor/dictionary/JSON and raw nested validation share one narrow policy.
   All finite values, coercions and scientific expressions stay unchanged.
2. **Check final DCF or valuation scalars only.** Already insufficient: malformed
   bounds can produce finite outputs. It also leaves configuration JSON invalid.
3. **Replace nonfinite settings with defaults or absent growth.** This hides an
   invalid requested configuration, changing clamping or terminal-growth fallback.
4. **Broaden rate/growth/count domains or reconstruct unchecked instances.** Those
   are separate compatibility and financial-model decisions. They are not needed
   to reject nonfinite ordinary configuration and are not adopted here.

## Decision

Add only allow_inf_nan=False to DcfAssumptions' existing ConfigDict. Preserve
frozen=True, every field/default/coercion, the discount>terminal validator, all
finite ranges (including inverted growth bounds), projection-year behavior,
JSON shape and all growth/DCF/valuation arithmetic. Do not introduce recovery,
None/default substitution, bounds ordering or new economic assumptions.

New invalid ordinary configuration raises ValidationError before producer use.
Raw nested configuration dictionaries/JSON receive the same field validation;
existing instances and unchecked model copies remain outside this constructor
policy. Custom assumptions are forwarded by both existing value-provider APIs;
ordinary construction refusal happens at the caller. Scoring remains outside
their history-acquisition fallback; no catch or provider behavior is changed.
Default CLI/scorer assumptions remain finite; no actual override run is inferred.
No parser, schema-field, screen/graduation threshold, v14 or generated data changes.

## Consequences and verification

Configuration JSON no longer silently turns newly constructed nonfinite knobs
into null. Earlier invalid instances and historically lost configuration cannot
be repaired by this guard, and general assumption disclosure remains separate.
Earlier construction can change which invalid-input error is observed; no
universal exception-message or unchecked-instance safety equivalence is claimed.

Write failing direct/dictionary/JSON, nested-result and actual-bound witness tests
before the one-keyword edit. Use Hypothesis for finite model JSON round trips,
retain provider/default/finite controls, replay 90 complete finite configuration
and producer claims and exact whole-module AST except the keyword, obtain final
independent reviews, then run foreground make check-all and verify exact CI after
individual publication. Removing the keyword reverses the policy and reopens
ordinary-construction F325; do not edit this accepted ADR.

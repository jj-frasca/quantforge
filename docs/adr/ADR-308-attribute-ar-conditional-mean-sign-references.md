# ADR-308: Attribute explicit AR conditional-mean sign references end to end

- **Status**: Accepted
- **Date**: 2026-10-17
- **Deciders**: Codex autonomous session 25, ISO 2026-W42
- **Resolves**: FINDING-155 production opt-in gap
- **Extends**: ADR-041/053/055/103/158/223/247/294/307

## Context

The AR source returns drift plus a centered AR state. Its conditional mean is
`phi * lagged_return + drift * (1 - phi)`. The legacy reference omits that
intercept. ADR-223 provides the corrected helper with explicit known-law inputs,
but measurement, collection, comparison and presentation cannot currently retain
which reference produced the denominator. A producer-only change would lose its
attribution or mislabel a reference change as a catalog improvement.

Missing historical metadata cannot identify the reference method or drift from
an AR edge label, because callers can supply externally measured score arrays.
Neither sign rule certifies cost-aware optimality or a realized-sample Sharpe
maximum. F173 is a historical descriptive audit; no frozen cohort is rerun here.

## Options Considered

1. **Explicit opt-in with closed method/drift identity across all consumers.**
   Pro: exposes the existing corrected helper honestly while preserving defaults
   and historical records. Con: requires one coherent backend/frontend slice.
2. **Producer-only switch or opaque companion scores.**
   Pro: smaller local change. Con: collection discards attribution and comparison
   or display misstates the denominator; duplicates the already available helper.
3. **Silent replacement, inferred drift, or a search-fingerprint change.**
   Pro: superficially fewer choices. Con: changes historical meanings, invents
   source provenance or wrongly attributes reference arithmetic to gate/search.

## Decision

Adopt option 1. Add optional nullable `ar1_reference` to PowerCalibration and
PowerSweep. The frozen, always-revalidated closed AR1Reference shape carries
`method` and `drift`: `ar1_phi_lag_sign_v1` requires null drift;
`ar1_conditional_mean_sign_v1` requires an explicit original finite float-representable nonboolean
Real drift normalized to float (normalization overflow raises ValueError). Reject unknown fields/methods. Bind known metadata
to edge ar1; each known-reference cell supplies phi, while sweep headers bind
edge/reference. Conditional cells additionally require stationary phi. Retain the legacy finite-phi domain. Do not infer source law from frames.

Measurement accepts optional explicit reference metadata. Conditional mode uses
the unchanged ADR-223 helper for gross cost0 and net DEFAULT_COST_RATE. Reject
contradictory inputs, external reference arrays and conditional achievable scores
before scorers/search. Default scorer calls and arithmetic remain exact. Newly
measured ordinary phi+ar1 output records explicit legacy metadata; odd legacy
custom-edge phi and externally supplied arrays retain unknown metadata.

Authoritative sweep construction/reconstruction and collection bind header and
cell reference identities, including unchecked copied inputs. Capture comparison
refuses known/unknown or unequal method/drift after existing header/search guards; malformed internal metadata may fail
authoritative reconstruction earlier, as structurally invalid artifacts do;
None/None retains existing historical comparison semantics. Reference identity is
separate from gate/search/history identity. Detection-only probability-DSR
comparison retains its joint-count semantics and existing guards; central sweep
metadata coherence still applies.

The AR driver adds `--ar1-reference-method legacy|conditional_mean` and `--drift`.
Default legacy calls stay exact. Conditional mode requires explicit drift and
passes that same value to source and measurement; legacy mode forbids drift.
Both flags enter ADR-307's value-position registry. No workflow changes/dispatch.
All reports name explicit method/drift or unknown and describe selected in-sample
reference-relative ratios, preserving cost and nonoptimality qualifications.

API model inheritance retains metadata. Frontend Zod retains optional nullable
closed shapes without scientific revalidation (strict reference objects inside
the discriminated union; enclosing historical schemas unchanged). AR captions distinguish explicit
legacy, conditional with exact served drift rendered using String(value), and historical unknown. Preserve
band wording, all served values/counts and backend compatibility verdicts; keys
must support multiple or duplicate AR identities without deduplication. Search
compatibility MATCHED does not certify reference equivalence.

## Consequences and reversal

Legacy arithmetic, underlying helper/formula/source, search/gate thresholds,
accounting-v14 and historical artifact bytes remain unchanged. This establishes
a supported opt-in procedure, not newly measured power, source-law certification,
net-cost optimality or a sample maximum. F159 remains separately open. Data JSON
files and frozen cohorts are read-only; no new search or source draws are needed.
Reversal can remove the opt-in producer while retaining readers for attributed
records; never silently strip identity or relabel historical measurements.

## Verification

Observe real RED before backend/frontend implementation. Mock generation/search
for wiring, validate scalar and contradiction refusals before scorers, test
unchecked model copies and header/cell identity, capture refusal and unchanged
detection-only comparisons. Preserve existing tests and helper bodies. Test CLI
same-drift dispatch and positional collisions; API/Zod/caption flow including
zero/negative/tiny drift, unknown historical data and multiple AR variants.
Compare the pre-change historical PowerSweep fixture after excluding only new
reference metadata, and verify raw artifact hashes. Run focused checks, parent
scope review, full foreground make check-all, individual push and exact master CI.

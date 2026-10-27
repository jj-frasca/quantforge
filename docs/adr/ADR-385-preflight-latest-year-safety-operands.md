# ADR-385: Preflight latest-year financial-safety operands

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session7, ISO2026-W44
- **Resolves:** FINDING-327 within latest-year financial_safety consumption
- **Extends:** ADR-029/155/384; earlier source refusal precedes ADR-384 output refusal

## Context

After ADR-384, NaN retained earnings can still compare False and become a favorable
finite quality0.5 accepted by FundamentalRecord. Infinite ratio denominators can
become finite zero; missing peers or zero denominators can hide other invalid
operands. Output validation cannot reconstruct those inputs. Independent data and
research reviewers confirm synthetic witnesses and approve this bounded policy;
no actual vendor, graduate or trading effect is established.

## Options Considered

1. **Preflight five latest-year safety operands (chosen).**
   - Pro: rejects erased invalidity before ratios or boolean evidence are formed,
     without changing shared Annual construction or other scorer policies.
   - Con: rejects present invalid operands even when their ratio previously was
     unused due to missing peers or zero denominators; error precedence changes.
2. **Guard only retained earnings or operands of nonmissing ratios.**
   - Pro: fewer new refusals.
   - Con: leaves nonfinite-to-finite division or shortcut-erased invalidity under
     the same safety-input claim and complicates the validity contract.
3. **Validate all Annual/history fields globally.**
   - Pro: could protect other consumers and earlier acquisition boundaries.
   - Con: changes valuation/provider availability and prior-year policy, requiring
     a broader invalid-versus-unavailable decision and separate compatibility work.

## Decision

Immediately after financial_safety selects its latest year, inspect fields in this
order: total_assets, total_equity, total_current_assets, total_current_liabilities,
retained_earnings. A present nonfinite operand raises plain ValueError naming that
field, before any safety arithmetic, missing/zero shortcut or boolean comparison.
Keep empty-history behavior, None and every finite native operation/range/threshold
unchanged. Retain ADR-384 output validation: overflow from finite operands still
raises ValidationError. No new catch, fallback, numerical recovery or skip policy.

## Consequences

New safety claims cannot erase nonfinite values from these five latest-year
operands. Availability is deliberately stricter even where another valid distress
leg already vetoes or an invalid operand's ratio would otherwise be absent. The
first invalid field determines the error; no aggregate-errors claim is made.
make_distress_provider still evaluates after its history-acquisition try, so
consumer ValueError propagates rather than becoming None. A sweep scoring error
may fail its shard before writing. Update ADR-384 producer tests to distinguish
new upstream plain ValueError from retained downstream ValidationError, while
keeping direct model refusal and no-fallback assertions.

Only this latest-row consumer changes. Older rows, global Annual/history
construction, unrelated fields/scorers, F-score methodology, PIT/period identity,
unchecked-instance provenance and historical records remain separate. No schema,
search/gate threshold, accounting-v14 or generated-data change occurs.

Use actual pre-code RED, finite/None Hypothesis controls, missing-peer/zero cases,
provider counterveto/order controls and finite-source-overflow controls. Replay
324 complete ordinary claims, 14 constructor/JSON controls and whole module AST
except the exact guard/import. Obtain final independent reviews and foreground
full gates before safe individual push and exact CI verification.

## Reversal

Remove the five-field preflight and math import. That restores FINDING-327 while
leaving ADR-384 output construction validation intact.

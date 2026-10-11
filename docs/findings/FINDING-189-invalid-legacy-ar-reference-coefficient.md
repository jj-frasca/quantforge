# FINDING-189: Invalid original AR coefficient can obtain finite reference scores

- **Status:** Corrected by ADR-240
- **Date:** 2026-10-11
- **Scope:** Direct legacy oracle_sharpe original phi after ADR-233
- **Decision:** ADR-240

## Evidence

On ordered closes [100,101,100,102], phi=False produces gross Sharpe zero,
phi=True produces about -15.821858, and phi=NaN produces zero. On flat ordered
closes [100,100,100], phi=+Inf or -Inf produces zero. Multiplication erases boolean
provenance or converts invalid original coefficients into all-missing predictions.
The generic scorer legitimately treats missing means as flat, but that convention
cannot establish original model evidence. Independent review reproduced these
cases exactly. No corrupt committed artifact or revised power count is inferred.

## Correction boundary

Validate original finite real nonboolean phi without substituting converted
operands. Preserve existing finite domains, native sign/lag/return/cost behavior
and defaults. Document original-phi-before-source precedence; keep valid-phi
source/cost ordering. No added stationarity domain or mixed-type recovery.
FINDING-155's drift/attribution issue and FINDING-159 remain Open.

## Verification

Pre-code TDD observed 28 failures and 28 preserved cases. The one validation-only
call was then added, retaining the original multiplier. Parent affected reference
suite passed 463 tests; independent affected suite also passed 463 tests.
Final independent review approved 208 checks: 180 exact native scalar/calendar/
cost/ownership scores, 12 empty/short/flat parity cases and 16 original coefficient/
source/cost precedence/refusal checks. Removing the call restores the prior scorer
AST. Full foreground make check-all passed 4672 backend and 363 frontend tests,
with lint, strict types and coverage green.

# FINDING-182: Reference cost evidence can bypass scalar validation

- **Date:** 2026-10-09
- **Severity:** Medium — malformed accounting inputs can produce measured-looking scores
- **Status:** Corrected by ADR-232
- **Affected:** oracle_sharpe_of and historical oracle_sharpe

## Reproduction

On ordinary closes [100,101,100,101,100], generic constant-long scoring accepts
cost_rate=True and reports -8.04092955809243; historical phi=-0.3 scoring accepts
it and reports -20.695577864235624. numpy boolean False is also accepted. The
explicit-drift AR helper already rejects booleans under ADR-223.

On complete short closes [100,101,100], both generic/historical entries return
0.0 with cost_rate=NaN, positive infinity, True or numpy False. Their legitimate
short-history shortcut bypasses the derived finite-return guard in ADR-229.
Strings and complex costs currently raise incidental TypeError; negative infinity
already raises ValueError. These results concern deterministic malformed direct
calls, not corrupted artifacts, new searches or changed detection rates.

## Proposed boundary

At the shared scorer, require original finite float-representable real nonboolean
cost evidence before existing negativity and short-history checks. Preserve the
original cost operand for native arithmetic, rather than silently retyping valid
numpy scalars. Preserve original negative-value comparison, including tiny exact
negative Real values that could round to signed zero. AR wrappers inherit the
shared boundary; existing explicit-law checks remain unchanged. Do not cap costs,
change defaults, modify prediction policy, thresholds, identities or generated data.

ADR-232 records the decision before implementation. Observed TDD, independent
review and full foreground gate are required before delivery.

## Correction verification

TDD observed 56 failures and 71 preserved cases before the single validation
call. All 356 parent-focused cases passed. Independent final review approved
all five paths with 499 relevant tests, 14 exact existing AR/band producer
comparisons and three finite huge-cost flat cases. Original cost operands and
exact-negative comparisons remain intact. Full foreground `make check-all PYTEST_WORKERS=8` passed: 4,161 backend and
363 frontend tests, with lint, typing and coverage green.

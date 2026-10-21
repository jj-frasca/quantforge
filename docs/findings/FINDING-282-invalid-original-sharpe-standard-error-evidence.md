# FINDING-282: Invalid original Sharpe standard-error evidence is accepted

- **Date:** 2026-10-20
- **Status:** Resolved by ADR-334
- **Scope:** sharpe_standard_error original score/history evidence

## Evidence and meaning

The public helper checks holdout_years<=0 only. Actual pre-fix calls produce:

- (score0, yearsInf): SE0.
- (scoreTrue, years1) and (score1, yearsTrue): SE1.0009915718846623.
- (scoreNaN, years1): NaN.

Parent and independent probes reproduce these outcomes. Zero uncertainty at
infinite history is the formula's limit; it is not supported finite observed
track-record evidence. Boolean and NaN values likewise do not identify the
advertised real score/history inputs. This is an original-domain contract
failure, not a changed model formula or proof of a production statistical claim.

## Mitigation and limits

The inverse frontier checks positive finite years and finite derived SE.
Reference/capture consumers use validated native floats and check derived
outputs. These mitigate ordinary producer exposure, without establishing this
standalone primitive's original-evidence boundary. No actual production
occurrence, affected graduate, changed capture/frontier result or rate is
established. General inverse-frontier scalar/count hardening is outside scope.

Native integer-square wrap was a distinct unresolved arithmetic defect at this boundary
(subsequently repaired separately by ADR-335 / FINDING-283):
int8(100) gives SE1.015749 versus Python100 giving4.565224; int8(12) can give SE
below the null SE. Original finite Real validation alone does not repair it.
This unit must not claim otherwise. Native zero squares are legitimate at
Sharpe zero and can be harmless after tiny floating underflow because the
formula adds one; separate arithmetic work needs its own domain analysis.

## Resolution

ADR-334 adds inspection-only finite nonboolean Real checks, history first,
retaining original positivity/operands and the exact return expression.
Parent froze 60 native scalar outcomes and 24 complete frontier payloads,
SHA256143038c96b892569b379e511634909c42a31037072b06fea4c78837d12a74123.
The known wrapped controls certify this slice's compatibility only.
Actual preimplementation TDD recorded 29 failures and 18 controls. The final
47 new tests pass; independent research review passed 122 new/frontier tests,
all 60 scalar outcomes, all 24 frontier reports and the prior runtime AST audit.
Known wrapped outcomes remain compatibility evidence only. Independent extra
checks cover both inspection exception branches and wider-real refusal.
Fresh foreground make check-all passed 13,513 backend and 566 frontend tests,
including lint, formatting, typing and both coverage gates. No threshold, v14
estimator, generated record or frozen cohort changes.

# FINDING-202: Direct factor score publishes wrong universe evidence

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — standalone scores publish contradictory component identity
- **Scope:** score_forward supplied evidence attachment
- **Decision:** ADR-253
- **Prior art:** ADR-140/FINDING-071, ADR-149/FINDING-079, ADR-252/FINDING-201

## Evidence

Independent synthetic reproduction uses a valid position and exact six-column
panel. Supplied evidence with only five components, OUTSIDE replacing S0, or
reversed component order produces a standalone score in both 399-bar and zero-bar
branches. Complete CrossSectionalPosition attachment rejects all six cases.
Score-level evidence validity and uniqueness cannot establish target membership.

The managed provider already supplies the complete ordered component evidence.
This is a direct attachment gap, not observed corrupt book records, broker actions
or measured false graduates. No real source, cohort, workflow, search, broker or
generated record was changed.

## Correction and verification

ADR-253 specifies authoritative early leaf reconstruction plus the existing
normalized position/evidence identity comparison. Independent pre-code review
preserves 12 exact complete native score comparisons for absent/model/raw-dict
evidence, normalized universe labels and zero/nonzero windows; all 125 current
forward tests pass under a scratch wrapper.

Before implementation, seven membership/order/early-refusal regressions failed
while 12 preservation cases passed. All 167 affected tests pass after the entry
evidence block. Independent final review approves those tests and 48 exact
complete published-baseline score JSON comparisons across four strategies, static
maps, normalized/native labels, absent/model/raw-dictionary evidence and both
forward windows. Position, prices and evidence inputs remain unchanged. Removing
only the entry block restores the complete published-module AST. Invalid copied
leaves refuse with ValueError before calendar access. The full foreground gate
passes 5,105 backend and 363 frontend tests, with 97.77% backend and 97.63%
frontend statement coverage; lint and strict typing pass. No evidence is
fabricated; native revision/source checks, arithmetic, schema and thresholds stay
unchanged.

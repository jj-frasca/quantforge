# ADR-104: Price the whole searched procedure in PBO

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** Codex autonomous session 6 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-036
- **Supersedes in part:** ADR-046 decision 6
- **Extends:** ADR-036, ADR-039, ADR-044, ADR-046, ADR-048

## Context

ADR-046 corrected DSR and MinTRL to price every concrete configuration and the final cross-family
selection, but deliberately left PBO and parameter stability family-local. That grouped two
different concepts. Parameter stability is a neighborhood diagnostic and has no coherent meaning
across unrelated strategy families. PBO is a CSCV measurement of whether the configuration selected
in sample retains its rank out of sample; its population must therefore include every configuration
the production selector can choose among.

FINDING-036 shows that the gate currently receives only the winning family's PBO. The overall
family argmax and longitudinal adaptive-refinement candidates are absent even though they are part
of the same selection procedure whose finalist is sent to the locked holdout.

## Decision

For each production search:

1. retain the per-bar return vector for every concrete candidate already evaluated on the search
   handle;
2. after optional adaptive refinement, compute one CSCV PBO over their complete `(T, N)` matrix;
3. write that procedure-level PBO to every persisted family-finalist summary and to the selected
   `ValidationReport` sent to `GraduationGate`; and
4. keep parameter stability and walk-forward/purged-CV family-local, because those diagnostics
   answer family-specific neighborhood or reselection questions and are not changed here.

The longitudinal search uses its existing ten CSCV groups; the cross-sectional search preserves
its explicit `pbo_splits` input. Candidate allocation, refinement, finalist selection, holdout
sealing, and `GateConfig.pbo_max` remain unchanged.

The calibration search fingerprint's accounting-method component must advance. An artifact from
the family-local PBO procedure is not evidence for the whole-search PBO procedure even when every
grid and threshold is identical. No workflow is dispatched and no generated data is edited by this
decision.

## Alternatives considered

- **Keep family-local PBO and describe it only as a diagnostic.** Rejected: it is a live graduation
  gate, not merely a displayed diagnostic, and the gate acts on a winner selected outside its
  measured family.
- **Compute PBO over family finalists only.** Rejected: each finalist was itself chosen from a
  parameter grid. Collapsing first discards the within-family selection that PBO already measures.
- **Make parameter stability global too.** Rejected: parameter distance across heterogeneous
  strategy families is undefined; ADR-046 was right to keep this metric local.
- **Change `pbo_max`.** Rejected: the defect is the measured hypothesis family, not the threshold.

## Consequences

- The PBO gate now measures the complete current search that produced the locked-holdout finalist.
- A low within-family PBO can no longer conceal rank inversion introduced by choosing among many
  families or by adding a refined grid.
- New trials carry one procedure-level PBO across their compact family summaries; historical rows
  retain their original family-local values and remain attributable through search identity.
- Ordinary null and power artifacts must be refreshed through their sole-writer workflows before
  quoting PBO component rates for this procedure. This ADR does not authorize dispatch.

## Reversal

Restore each finalist's family-local report PBO before the gate. That would again omit the
cross-family and refinement selection documented in FINDING-036 and is not recommended.

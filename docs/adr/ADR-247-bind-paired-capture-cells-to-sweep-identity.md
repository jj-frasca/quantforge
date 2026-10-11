# ADR-247: Bind paired capture cells to sweep identity

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 33, ISO 2026-W41
- **Resolves:** FINDING-196
- **Extends:** ADR-057, ADR-103
- **Relates to:** ADR-051, ADR-158, ADR-246

## Context

FINDING-035/ADR-103 bind nested probability-comparison evidence to its advertised
procedure. The separate capture consumer reconstructs cells but only matches the
sweep headers. Direct persisted sweeps can contain cells from another process,
gate, search or history, yet produce an attributable delta under matched headers.
Reconstruction freezes evidence; it does not prove those nested identities.

The capture collector advertises int(median(n_bars)) for each recorded cell and
requires those summaries to agree. It allows partial, heterogeneous and absent
legacy histories, including cells with absent histories mixed with cells with
recorded histories. Importing
ADR-103's strong-cell completeness rule would change valid capture evidence.

## Options Considered

1. Bind cell identity at the consumer using the collector's existing descriptive
   history contract. Protects persisted input while preserving legacy semantics.
2. Trust headers/constructor provenance. Persisted models bypass the collector.
3. Require complete equal histories as in probability inference. Adds a stricter
   evidence regime than this descriptive capture comparison currently uses.

## Decision

Preserve earlier header-to-header and duplicate-key refusals. Before comparison
mappings or endpoint reading, bind every cell's edge, gate and search versions
to its header. For each recorded history require the unchanged native
int(median(cell.n_bars)) to equal the header's n_bars. Refuse arithmetic overflow
while forming that summary with ValueError; do not recover or change the median.
For nonempty sweeps with all histories absent, require the collector's zero marker.

Retain partial/heterogeneous histories, mixed known/absent histories, all-absent
zero headers and direct empty-sweep comparison behavior. Do not require array
length equality, per-bar uniformity, a sample floor or new process domains.
Embedded verdict binding, producer/schema changes and reference qualifications
remain separate. No selection, estimator, threshold, source or artifact changes.

## Verification and reversal

Observe both-side nested process/version/history refusal regressions before code.
Preserve exact collector-built legacy/modern comparisons and native history
summaries, including fractional median truncation and original huge integers.
Independently review and run the full foreground gate before delivery.
Removing the consumer bindings reopens FINDING-196.

# ADR-242: Protect the published SIC single look

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 33, ISO 2026-W41
- **Resolves:** FINDING-191
- **Extends:** ADR-161
- **Relates to:** ADR-099, ADR-100

## Context

ADR-161 fixes one SIC composition-test look and reports its completed result.
The driver nevertheless reads the growing pools, computes another test and
overwrites an existing destination. Two independent scratch-only reproductions
confirmed this path; neither recomputed the actual cohorts nor modified their
published evidence.

## Options Considered

1. Refuse an occupied destination before inputs and publish exclusively.
   This prevents ordinary post-publication reruns and replacement, but does not
   serialize two concurrent invocations that both start without a destination.
2. Rely on the operator reading ADR-161. No extra code, but the existing driver
   already contradicts that convention and silently replaces evidence.
3. Add a persistent pre-computation reservation and recovery protocol. This also
   serializes absent-start invocations, but introduces interrupted-run recovery
   state beyond the reproduced published-result defect.

## Decision

Refuse an existing output path, including directories and dangling symlinks,
before store construction, input reads or inference. Return nonzero with an
ADR-161 single-look explanation. Publish an absent destination using exclusive
creation and return nonzero on FileExistsError without changing the winner's
bytes. No force, deletion or rerun option is added.

Keep the estimator, seed, resampling counts, cohort selection, run gate,
classification predicates and JSON structure unchanged. The committed result
remains read-only; no actual-cohort rerun is authorized. A follow-up measurement
still requires its own pre-registration under ADR-161.

## Verification

Observe failing scratch-only tests first: occupied files/directories/symlinks,
no inputs or inference before refusal, late publication collision and byte
preservation. Protect first publication, unchanged run-gate failure and refusal
on a subsequent invocation. Review independently and run full foreground gates.

## Consequences and reversal

A published result stops routine remeasurement and cannot be overwritten by a
late competing publisher. Exclusive creation protects publication; it does not
promise atomic completion after process failure or a concurrency-wide analysis
lock. Those need separate recovery/reservation design. Removing the guards
reopens FINDING-191. No validation threshold or generated evidence changes.

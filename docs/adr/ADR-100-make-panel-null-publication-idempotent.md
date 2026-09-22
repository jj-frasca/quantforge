# ADR-100: Make panel-null recovery publication-idempotent

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-032
- **Extends:** ADR-030, ADR-087, ADR-099

## Context

ADR-087 permits exactly one post-consolidation operation: publish the already completed panel-null
artifact's validated exact bytes. The recovery command currently replaces the generated destination
unconditionally, and its workflow always attempts a commit. Source validation proves which bytes
may be published, but it does not define what may happen when the durable destination already
exists.

Because the path represents one fixed 400-panel look, publication state has only three legitimate
cases: absent, byte-identical, or conflicting. Git rebase behavior is too late and too incidental to
serve as the invariant that distinguishes them.

## Options considered

1. **Rely on the eventual rebase/push result.**
   - Pro: no code change.
   - Con: a different destination is overwritten locally first, and identical publication still
     creates a misleading recovery commit attempt.
2. **Always refuse recovery when the destination exists.**
   - Pro: no overwrite is possible.
   - Con: harmless retries cannot prove completion idempotently and would red after a lost workflow
     response or repeated operator invocation.
3. **Compare exact bytes at the recovery boundary.**
   - Pro: absent publishes once, identical succeeds as a no-op, and different fails before mutation.
   - Con: workflow commit logic must explicitly handle the no-change case.

## Decision

Choose option 3. Only after full artifact and authoritative run validation, recovery checks the
destination if it exists. Exact byte equality returns the validated calibration without rewriting
the path. Any byte difference raises before directory creation, temporary-file creation, or
replacement. An absent destination retains the existing atomic exact-byte publication path.

The recovery job checks out current `master`, making the compared destination authoritative rather
than the recovery dispatch ref's historical view. It then stages the fixed generated path and exits
successfully without committing or pushing when the index has no change. Concurrency remains the
cross-run serialization boundary; the comparison is the durable one-look publication invariant
within a run.

## Consequences

- Repeating exact recovery is a clean no-op and cannot create a second generated commit.
- A different durable measurement at the fixed path cannot be replaced through recovery.
- First publication after a push-only failure remains atomic and byte-for-byte identical to the
  validated source artifact.
- No seed, panel, statistic, inference input, gate, generated artifact content, or validation
  threshold changes.

## Reversal

Removing the destination comparison restores FINDING-032 and is unsafe after the fixed measurement
has been published.

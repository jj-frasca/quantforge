# ADR-383: Synchronize exclusive panel-shard writes

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session5, ISO2026-W44
- **Extends:** ADR-081/085/090/158

## Context

The panel-null scratch-shard writer revalidates its payload and exclusively
creates its destination, but closing its buffered text stream does not request
file or parent-directory synchronization. Repository-owned evidence writing can
provide that explicit boundary without copying a serializer-specific scratch
helper. No lost artifact or failed physical persistence has been demonstrated.
Independent data and research reviews approve this narrow engineering slice.

## Options considered

1. **One byte writer and one shard consumer (chosen).** Keep serialization and
   scientific validation with the caller; add ordered synchronization requests.
2. **Rely on buffered close.** Keeps the present behavior but provides no explicit
   file/parent synchronization boundary.
3. **Build an artifact framework or migrate every writer.** Unnecessary scope;
   source/cohort/final writers and historical scratch scripts stay unchanged.
4. **Replace/rename on failure or retry.** Conflicts with preserving the original
   exclusive claim and can hide a failed evidence write.

## Decision

Add `write_exclusive_bytes(path: Path, payload: bytes) -> None`. Require an existing
parent. Open with `xb`, write the exact bytes once, reject a short write, flush,
fsync the file, then close it. Open the parent read-only, fsync its descriptor,
and close that descriptor in a finally block. Propagate creation/write/flush/
sync/close errors. Never create parents, retry, unlink, truncate or replace.
After creation, failure retains the claimed file in the absence of external
mutation; bytes may be incomplete. Existing files and symlinks refuse creation.

Adopt only in `save_panel_null_shard`: revalidate the existing model, complete
`model_dump_json() + "\n"` and UTF-8 encoding before claiming the path, then call
the byte writer. Successful bytes match the previous Linux/macOS text writer.
Serialization failure now occurs before creation; its precedence against an
existing destination can change. Do not claim universal failure equivalence or
Windows newline compatibility. Keep all model fields, identities, source/seed/
index checks, search/gate policy, statistical operations and thresholds unchanged.

This targets the project's POSIX Linux/macOS environments. Unsupported directory
sync or filesystem errors fail visibly after file creation; no silent fallback.
Success means the OS synchronization requests returned. It does not prove
hardware persistence, make publication atomic, prevent readers seeing partial
files, or protect against hostile/concurrent parent-directory replacement.
The helper supplies no JSON policy, schema, hashes, root confinement, recovery
or execution authorization. Frozen protocols and artifacts remain untouched.

## Verification and consequences

Before implementation, observe existing-shard tests fail because synchronization
is absent and injected sync errors are not propagated. Then test exact bytes,
ordered flush/file-sync/close/parent-sync, exclusive collisions and symlinks,
missing parents, short writes and injected failures with retained claims and
descriptor cleanup. Reproduce complete pre-change shard byte/load claims and
compare the whole panel module AST except its writer and new import. Obtain
independent final review; run foreground make check-all and exact CI after push.

Retained pre-implementation evidence records three expected failing shard tests
(missing synchronization and both missing sync-error propagations), with 62
deselected tests. The completed focused suite passes 84 synthetic tests. Three
pre-change complete shard byte/load claims and the whole panel-module AST outside
the writer/import compare exactly. Independent data and research final reviews
approve the six-path unit; the data review additionally verifies descriptor cleanup
and UTF-8 encoding failure before absent/existing destination claims. These are
synthetic control-flow and byte-compatibility checks, not power-loss experiments.

Synchronization adds I/O latency and can surface errors after complete bytes
exist. A failed write is not permission to retry or repair a frozen attempt.
No cohort is run, regenerated or inferred from these synthetic tests. Removing
the helper adoption reverses this synchronization policy; it does not repair any
historical artifact or establish null-law execution readiness.

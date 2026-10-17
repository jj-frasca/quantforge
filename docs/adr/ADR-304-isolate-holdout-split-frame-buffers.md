# ADR-304: Isolate holdout split numeric buffers and axes

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 23, ISO 2026-W42
- **Resolves:** FINDING-259
- **Extends:** ADR-016/024/137/165/302

## Context

Positional iloc slices retain their whole source's numeric owner. On ordinary
canonical float OHLCV, search_frame['close'].to_numpy(copy=False).base exposes the
full source block, including actual held-out prices. The returned column view is
readonly under pandas 3 Copy-on-Write, but its public NumPy owner is writable:
changing a held-out coordinate changes the actual sealed tail and working source.
No private pandas manager, sealed-object access or arbitrary memory tool is needed
to recover prices starting only from the search frame.

Both public splitters exhibit this route. ADR-165 isolates the retained dataset
snapshot, but splitting its independent full working copy still shares that copy's
owner. No current catalog use of base/as_strided/ctypes was identified, and no actual
strategy lookahead, false graduate or affected historical cohort is established.

## Options considered

1. Materialize independent numeric/axis copies of both split portions: closes the
   demonstrated owner route and source-alias mutation at the split boundary.
2. Trust readonly views or pandas Copy-on-Write: does not hide the writable full
   owner accessible through public NumPy base chains.
3. Copy only the search portion: hides future prices there but leaves the sealed
   scoring input mutable through an external source owner.
4. Wrap or freeze every direct constructor/frame read: much broader API and
   performance policy; trusted direct construction and writable frames stay separate.

## Decision

After existing fraction, whole-calendar and size validation, materialize independent
copies of both positional portions before returning either splitter's result.
Use deep numeric data copy plus explicit deep index and column copies. DataFrame
copy alone retains datetime index storage; public index.asi8 must be isolated too.
Preserve exact logical values, dtypes, row/column order, axes and split geometry.
No dtype rejection, sorting, deduplication, floor or scoring change is introduced.

Move the existing dataset._copy_frame implementation unchanged into research.frames
as public copy_frame. Dataset imports it as _copy_frame so descriptor calls and the
existing refusal-before-copy spy remain exact. Both splitters use the shared helper;
bars_to_frame conversion and dataset ownership semantics remain unchanged. This
keeps one numeric/axis snapshot recipe without coupling core splits to vendor data.

Accept bounded O(source-size) additional allocations at each split. Search and
returned panel frames remain ordinary writable pandas frames; direct constructors
are not given a new capture/copy-on-read contract. This isolates canonical numeric
buffers and axes, not recursive mutable object cells, arbitrary attrs graphs,
external globals, hostile introspection or unrelated strategy causality defects.
Do not advertise a Python security sandbox or universal pandas-object immutability.

Deep copies can consolidate blocks and change strides. Formulas remain unchanged,
but a few measured baseline matches cannot prove universal bitwise equivalence for
all native reductions/layouts. Check representative layouts and public scientific
payloads exactly; investigate differences instead of loosening tolerances. No gate
threshold, search count recipe, configuration hash or accounting-v14 change is
intended. No historical cohort is rerun, relabeled or certified by this correction.

## Verification and reversal

Observe buffer-recovery/mutation RED before code. Test both splitters with distinctive
future-price sentinels, recursive public base chains, readonly view/writable owner,
source and returned-frame owner writes, public datetime asi8 storage, heterogeneous
numeric blocks and exact logical values/dtypes/axes across C/F/strided layouts.
Hypothesis verifies that changing only future rows cannot change the search frame's
reachable numeric owner. Keep existing guards/size behavior and all old tests.

Four new bounded standalone search/panel payloads are frozen before implementation,
excluding only fresh root UUID/time; compare every other field exactly afterward.
They are regression fixtures, not a null/power cohort or historical source retry.
Check exact helper relocation and unchanged descriptor/scoring AST, independent
review and foreground make check-all before individual push and exact CI.

Restore view-returning slices to reverse, reopening FINDING-259. The helper can
remain shared without changing dataset semantics. Never rewrite generated evidence.

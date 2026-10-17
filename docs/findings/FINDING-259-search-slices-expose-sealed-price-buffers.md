# FINDING-259: Search slices expose held-out prices through shared numeric owners

- **Date:** 2026-10-16
- **Status:** Resolved — ADR-304
- **Area:** numeric and axis ownership of both public holdout splitters

## Independent reproduction

Under pandas 3.0.6 and NumPy 2.5.3, construct eight unique ascending UTC dates with
finite float OHLCV: high3000+i, open2000+i, close1000+i, low500+i, volume10000+i.
Split with fraction .5/floors2, giving four search rows and four held-out rows.

Starting only from search['close'].to_numpy(copy=False), its readonly four-element
view has a public .base owner of shape(5,8). That writable owner contains the exact
held-out close values1004..1007. Recursive public base following suffices when an
intermediate view exists; no private pandas manager or sealed-frame access is
needed for recovery. Inspecting the known synthetic tail only verifies the match.

For both splitters, shares_memory(owner, heldout_close) is True. Writing the owner
coordinate containing1004 changes the actual first held-out close and source to
123456. Ordinary pandas iloc writes are isolated by mandatory Copy-on-Write, so
those passing controls do not establish public numeric-owner isolation.

Deep DataFrame copy separates price owners but does not itself isolate datetime
index storage: public index.asi8 can still retain the full eight-date owner.
Explicit deep axis copies are required for the separately stated axis contract.
Timezone-aware index.to_numpy makes an object copy and is an unsuitable negative
memory-sharing control for this case.

Report: `/tmp/qf-w42-s23-holdout-buffer-review.md`.
Receipt: `/tmp/qf-w42-s23-holdout-buffer-reproduction.json`.
The original probe completed measurement but failed JSON emission on a NumPy bool;
its separate corrected probe and dataset/index controls terminated successfully.
Original scripts/evidence remain preserved; no search/cohort/source file was changed.

## Attribution and limits

ADR-165 keeps the retained ResearchDataset snapshot intact. Its full working copy,
when split into views, still exposes the working held-out prices to the search
slice. Thus this route exists on normal numeric working frames, not only malformed
calendars or unvalidated direct input. It does not demonstrate any current catalog
strategy taking that route. Targeted static inspection found no base/as_strided/
ctypes operations in current strategy, search and validation code after excluding
module names in BaseStrategy imports.

No actual production lookahead, false graduate, historical contamination or changed
calibration rate is established. Python handles are not a hostile-code sandbox;
closing this ordinary public array-owner route does not prevent arbitrary stack,
global or OS-memory introspection or another strategy's causality defect.

## Correction and verification

ADR-304 gives both returned portions independent deep numeric buffers and explicitly
copied axes. The exact existing dataset helper moves to research.frames, with its
private dataset alias/descriptor calls preserved. Values, dtypes, axes, split guards,
geometry and scoring formulas stay. Direct constructors/returned-frame mutability,
recursive object cells/attrs graphs and historical evidence remain separate.

Additional O(source-size) allocation is accepted. Copies can change layout, so exact
matches of four new standalone regression payloads do not certify universal bitwise
native-reduction equivalence. Investigate mismatches; do not weaken any tolerance,
threshold, original property domain or frozen-source protocol.

Session23 observed all32 actual failures before runtime edits, preserved in
`/tmp/qf-w42-s23-copy-final-red.log` (32failed in6.99s). Session25 independently
reran the new ownership suite (32passed) and existing holdout/calendar/dataset/frame
cases (113passed); the parent focused regression set including panel engine cases
passed267 tests in12.32s, with three existing timedelta deprecation warnings.
No existing test or assertion was removed or weakened.

Independent review `/tmp/qf-w42-s25-research-expert-review.md` found no blockers.
Its17 source AST checks and parent `/tmp/qf-w42-s25-source304.json` confirm exact
helper relocation, unchanged dataset descriptor and scoring, and only copy wrappers
around the original splitter slices. Guards, geometry and other executable AST stay.

The independently rerun `/tmp/qf-w42-s23-copy-baseline.py --check` matched all four
prechange standalone scientific payloads exactly, excluding only fresh root UUID/time.
Baseline `/tmp/qf-w42-s23-copy-baseline.json` SHA256:
`0cd8daf537a0c0401bb6bc312397111c5fb897977beccf8d040512560e796c5f`.
These are bounded regression fixtures, not calibration cohorts, retries or evidence
of universal bitwise equivalence. Frozen incomplete AR/bootstrap evidence was untouched.

Session25 foreground `make check-all` completed successfully before commit:
12,251 backend tests, 97.40% coverage; 381 frontend tests, 97.66% statements;
backend Ruff/format/mypy184 and frontend ESLint/TypeScript all green.
Log: `/tmp/qf-w42-s25-check304.log`. No threshold, v14 fingerprint, generated
record or frozen source was changed.

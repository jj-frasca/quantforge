# ADR418 final-window evaluator: offline implementation evidence

This package supports ADR424's implementation of the already sealed ADR418
portfolio. It contains no market prices or new economic observation. Original
ADR418 protocol/cohort bytes, selections, deadlines, costs and strict screen stay
frozen. The real attempt root remains absent during implementation.

The original seal941dee7c2443f30e4433617a3d5070e6a8a80b60 passed push CI42227612894
on2026-11-06T13:46:49Z and hooks42227612864 on13:42:47Z, before the November9
14:30UTC deadline. `seal-publication-*.json` retains authoritative read-only GitHub
metadata retrieved during this implementation, without dispatching workflows.

`input-fundamentals.json.gz` and `input-roster.txt.gz` preserve COMPLETE original
7048 Git blobs, not projections or revised inputs. The fundamentals gzip is436389
bytes, below the unchanged500KiB file hook. `pinned-policy.json` binds both raw and
compressed input hashes and24 active source/quality/account code hashes from7048.
Its outer SHA256 is3d2e321c6b596352bc9f44d0f47e295698ca1969799ced816fa387be6308a4b0.
Independent data review verifies exact Git linkage in `portable-data.md`. Runtime
checks need no historical Git objects, network or current-pool fallback, so a
shallow checkout can perform offline conformance. This representation changes no
study inputs or source policy. Actual dependencies/wider imported modules are
separately attributed; equivalence to the old environment is not asserted.

Precode research and fresh nonimplementing data approvals are retained here.
The completed TDD and synthetic receipts are described below. Initial blocked
reviews remain historical evidence of the false float-tie screen, corrected
before release under ADR425.

The next economic observation remains the sole existing ADR418 final screen in
[2027-02-11T00:00Z,2027-02-12T00:00Z). The production entry point must refuse early,
expired, occupied or policy-mismatched attempts. No scheduler, cloud dispatch,
paid API, credentials or broker action is introduced.

## Completed offline conformance — session12 recovery

The inherited final four-case run completed before interruption at temporary
root `qf-adr424-synthetic-gm1kr8wm`. Recovery verified every manifest/payload hash
and every executed application hash against the unchanged current files. The
retained complete receipts are split by case to respect the existing500KiB
file hook; no source receipt is dropped. `conformance-manifest.json` binds the
four archives, original full summary and TDD/protected-file archive.

| Synthetic case | Requests | Source/DQ/dataset receipts | Result |
|---|---:|---:|---|
| Flat100 |413|413 each|COMPLETE, screenFAIL|
| Selected100 to163, others100 |413|413 each|COMPLETE, screenPASS|
| Every name100 to101 |413|413 each|COMPLETE, exact-tie screenFAIL|
| SPY unavailable after all eligible |413|412 each|UNEVALUABLE, no accounts/screen|

Identical-rising exact net returns are799/100100 for all three security legs;
EW and SPY contrasts are exactly zero. The decision uses strict rational signs,
not native float subtraction. Flat exact net returns are-2/1001. These fake
prices are conformance fixtures, not economic trials or evidence of alpha.
Full native accounts, equity paths, costs, turnover, drawdown, canonical sources,
original DQ reports and dataset evidence remain in each archive.

`tdd-and-protection.tar.gz` retains the original27-collected precode failures,
targeted durability/review/root failures, six exact-screen RED failures, final44
GREEN and original694-path hash baseline. The exact-screen RED includes the full
413-by64 false-positive tie before its correction. No old tests were changed.
Fresh independent research and nonimplementing data reviews each ran44 tests
successfully; both verified694 protected hashes. Research additionally matched
1000 separate funded-unit cash oracles and reconstructed all exact returns from
the retained source rows. Their reports and independent oracle are retained.
All review processes closed before the full repository gate.

Run offline reproduction from repository root (only temporary fake-source roots):

```sh
PYTHONPATH=backend backend/.venv/bin/python docs/evidence/ADR-424/reproduce.py
```

The independent reviewer's original script is retained byte-for-byte as
`independent-research-oracle.py.txt`, with its original backend working directory
and local receipt/baseline paths. Its report records that actual verification;
it is historical review evidence, not a portable invocation. To inspect portable
receipts independently, verify hashes and expand only into a new temporary
directory, then compare each case's file-manifest and source endpoints with its
result. All four archives contain their original START/code/dependency identity.
The real attempt root is absent. No source-policy, cohort, calendar, cost,
selection/trial accounting or financial-gate threshold changed. Alpha evidence
did not improve. This unit closes the missing evaluator implementation; actual
413-series coverage and the original future economic result remain unmeasured.

Fresh foreground `make check-all` completed with exit0:17,954 backend tests
(97.33% coverage),781 frontend tests (97.89% statements),563 formatted files and
strict mypy on202 sources. No source/test changes followed the independent
reviews. Full-gate verification does not change the study's unmeasured economics.

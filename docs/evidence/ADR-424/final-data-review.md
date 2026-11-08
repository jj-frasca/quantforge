# Independent nonimplementing data review — ADR424/425, W45 session12

Verdict: APPROVE the frozen implementation and existing portable input evidence. Final parent conformance package was not yet available during this review; its review remains separate. No tracked files were edited, no provider/network call was made, and the real registered root was never created.

Reviewed the data-engineer contract, ADR418/424/425, prospective source cold contract, all516 implementation lines, CLI, and all570 test lines. Root/window and complete-source boundaries conform to the frozen protocol: production CLI has no override, rejects early before prepare, checks again before exclusive root; root reservation and START receive file/directory fsync before factory; every attempt is marked before provider and rechecks its window after marker. Synthetic root validation checks absolute lexical and resolved candidates against lexical/resolved registered root and descendants. Tests exercise aliases and symlink escapes against fake temporary roots only.

The source provider defaults to pinned YFinanceAdapter with default one-attempt policy. The actual study code preserves canonical Decimal prices as serialized model dumps, original quality UUID/time/warnings, passing ResearchDataset evidence before calendar refusal, and exact ordered64-label coverage on413 names before account output. Expected source failures yield UNEVALUABLE with no subset accounts; unexpected method/storage failures propagate and leave the exclusive start incomplete. Deadline crossing retains received canonical source and original DQ report and yields INCOMPLETE without published accounts. No method claims prevention of bias or vendor authenticity.

Independent checks from repository root: all694 entries in /tmp/qf-w45-s10-424-protected.json matched byte SHA256; all24 active_policy_sha256 entries matched git show7048c785fd34fa0fc5b8357fc711929c7fe48fb9:path, and both decompressed portable full input blobs equalled those original Git bytes exactly. The actual registered root /tmp/qf-adr418-prospective-20261109-20270210 was absent, including as a symlink. Runtime policy manifests are scoped to listed active paths, not claimed as dependency/wider-import equivalence.

Ran backend/.venv/bin/python -m pytest -q -m 'not live and not integration' tests/unit/test_prospective_portfolio.py from backend: 44 PASS in26.31s, process exit0, closed. This includes full413x64 flat/rising/positive-tie and late source-failure cases; durable markers, deadline crossing, DQ/calendar failures and preservation, source tampering, immutable root aliases, exact Fraction tiny signs, mean-ratio accounting and nonfinite projections. Exact positive tie produces799/100100 for all security legs and zero EW/SPY contrasts, strict FAIL. Native funded_hold reports remain unchanged companions.

Frozen reviewed SHA256:
- backend/app/research/cross_sectional/prospective_portfolio.py: 9e75e908a2c2a68a8bd060a17fe0df1493a10134c06b8ceb576ec8d3d220ee3e
- backend/scripts/prospective_quality_value_study.py: 54e8721c377c0f275218dbf472ab5b6c1915e0e2d88490cc793f2a2d5bdb0798
- backend/tests/unit/test_prospective_portfolio.py: 58ebb5fd2d07f2544fa380ff913190950b2b182e7b66da20e00c2491ac1bd0f7

All review imports/test processes are closed. No economic alpha evidence improved; synthetic conformance verifies an evaluation capability only. Actual source completeness and eventual market outcome remain unresolved until the original sole February11 final window, with all prior frozen cohorts retained.

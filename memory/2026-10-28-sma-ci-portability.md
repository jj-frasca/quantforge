# ADR-392 CI score-oracle portability

Status: test-oracle repair locally verified; exact post-push CI is recorded in
the session ledger. The upstream numerical operation remains unisolated.

Symptom: master CI40685152281 at2dc5944d failed two newly added SMA tests;
16003 backend tests passed, frontend and pre-commit succeeded. Both failures
compared the engine-produced score20.251609905954115 with a decimal constant
20.251609905954144 copied from the local generated58-row fixture.

Root cause: the assertions encoded cross-runtime bitwise score identity, while
the contract requires equality with native engine scoring on supplied prices.
The cross-runtime last-bit discrepancy is observed; its upstream operation is
not isolated. No identical-array digest/intermediate audit proves whether fixture
transcendentals, reductions or another native operation explains it.

Reproduction before repair: a scratch pytest plugin moved fixture close[10]
one representableFloat64 step upward. The same two assertions failed with score
20.251609905954126 (2failed1.93s). This controlled different valid input proves
the constant oracle is brittle, not the cause of the Linux discrepancy.
Receipt: /tmp/qf-w44-s12-portability-red.log. Plugin is scratch-only.

Repair: construct the known1/2 SMA independently and compare the selector's
score exactly with BacktestEngine on the same materialized frame. Snapshot the
returned scalar before source mutation and compare exactly afterward. Preserve
all candidate-order, selected-ordinal, refinement, count and frozen-field checks.
No approximation tolerance, production source, statistic, gate, threshold,
accounting identity or generated record changes. The regression assertions stay
in backend/tests/unit/test_sma_selection.py; cold memory qualifies their scope.
Independent research review approved this test-only correction before patching.

Verification: controlled perturbed-fixture replay2passed1.84s; independent
ordinary45-test suite passed3.63s. Fresh foreground make check-all passed16005
backend and746frontend tests, coverage97.46%/97.88%, lint/format/types191PASS.
Exact post-push CI receipts belong to .claude/CODEX_RUNNING_STATE.md.

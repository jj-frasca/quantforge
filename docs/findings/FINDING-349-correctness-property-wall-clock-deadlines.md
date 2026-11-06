# FINDING-349: Implicit wall-clock deadlines reject numerical correctness properties

- Date: 2026-11-05, ISO 2026-W45 session 1
- Status: narrow test-execution setting correction; independent research review approved
- Found during ADR-413's full foreground gate, before any commit or push

The first full gate passed 17,782 tests and failed two existing properties solely
on Hypothesis's implicit 200ms per-example deadline. Alpha4's operative-hull test
took 352.33ms. The reference-prediction test took 283.94ms on the first execution
and 5.72ms on immediate recheck, producing Hypothesis's explicit unreliable-timing
failure. No financial assertion failed. Serial reproduction retained the Alpha4
deadline failure at 251.69ms while the reference property passed.

Inspection shows six full Alpha4 signal/weight/return/oracle calculations in each
example. One profiled unchanged body made 179,896 calls in 0.649s; profiler overhead
makes that observation unsuitable as a performance benchmark. The neighboring
Alpha9 operative-hull property already uses `deadline=None`. Neither failing
property specifies a runtime requirement: they check causal hull/purge geometry,
numerical identity, sign, turnover, and missing-startup behavior.

Add only `settings(deadline=None)` to these two properties and the necessary
imports. This explicitly removes the incidental wall-clock check; it does not
make code faster. Keep the entire original bodies, generated domains, default
example budgets, exact comparisons, tolerances and assertions. No test is skipped,
no production computation changes, and no DSR/PBO/MinTRL/holdout/universe-deflation
or other scientific acceptance threshold moves. This is a verification prerequisite
for shipping the bounded evidence report, not an additional alpha experiment.

Independent root-cause review approved the distinction and narrow scope before
the edit. Compare complete old/new test ASTs after removing only the two added
settings decorators and imports, then rerun both original properties plus the
new report suite and the entire foreground gate. Failure receipts remain in
`/tmp/qf-w45-s1-check413.log` and the ignored session ledger. Reversal removes
the two settings decorators/imports, restoring the incidental timing check.

Verification completed: both full test ASTs matched after removing only the
declared settings/import additions. Both original properties plus the new report
suite passed (14 tests, 19.30s). Fresh full foreground `make check-all` passed all
17,784 backend and 781 frontend tests, lint, formatting and types. No additional
production fix or scientific experiment was needed.

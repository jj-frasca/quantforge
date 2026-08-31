# FINDING-013: ADR-074's re-search was under-powered by choice, not by candidate scarcity

- **Severity:** Medium — no threshold, gate or graduation is wrong; a pre-registered experiment was
  spent at half the size available and its record tells the next session to keep waiting
- **Status:** Open; corrected by ADR-076, which freezes and re-sizes the sample
- **Found:** 2026-08-31 by autonomous session #16 while acting on ADR-074's closing instruction
- **Affected:** `ADR-074` §Measured, `RUNNING_STATE.md` session #15, `window_experiment_symbols`

## Finding

ADR-074's Measured section says the pre-registered re-search covered *"all **45** symbols that carry
ADR-068's benchmark at the long window and not at the short one"*, and its closing line — repeated
as the handoff's `Next session should` — says *"the candidate pool held exactly 45 today and grows
as the discovery records the benchmark on more symbols… re-run the same command when the candidate
pool reaches ~75 symbols."*

The candidate pool held **368**, not 45. `window_experiment_symbols(experiments, n)` returns
`candidates[:n]` after a seeded shuffle; `scripts/window_experiment.py 45` therefore searched 45
symbols because 45 was the command-line argument. The candidate set was never the binding
constraint.

## Evidence

- `window_experiment_symbols(PartitionedExperimentStore(data/research_pool).all(), 500)` returns
  **368** symbols today, and the store is unchanged since `cc2e742` (2026-08-30), which predates
  session #15. `git status` is clean, so the working-tree pool is that commit's.
- `scripts/window_experiment.py` prints `n=<excess_n> of <n_symbols> paired symbols`; a 4-symbol
  invocation today prints `n=4 of 368`.
- Session #15's own `pool_report.py` output, quoted in its handoff, reads *"368 symbols searched at
  both, 5446 → 9232 bars"*. The two counts coincide for a structural reason: a symbol is a candidate
  exactly when its long window carries ADR-068's benchmark and its short window does not, and the
  pre-ADR-063 short-window rows all predate that benchmark. The number was on the screen.
- `data/window_experiment/adr074_summary.json` records `"n_symbols": 368` beside `"excess_n": 45`.

## Impact

ADR-074's criterion was applied at n = 45 with a bootstrap half-width of 0.093 against an effect of
−0.074, so it returned inconclusive — an outcome ADR-074 predicted in advance and reported honestly.
The defect is not the reading but the sizing: 8× the sample was available at zero methodological
cost, and the recorded reason for stopping at 45 was a misreading of the driver's own argument.

The compounding harm is in the handoff. `Next session should` told the next session to wait for a
count that had already been exceeded by a factor of five, in a project whose candidate set only ever
grows — an instruction that would have deferred the decisive measurement indefinitely.

## Required correction

1. Correct the record in ADR-074's Measured section and in the handoff, rather than silently
   re-running (done here and in ADR-076's Context).
2. Size the re-run from the dispersion measured at n = 45 instead of from an availability
   constraint that does not exist (ADR-076 decision 2).
3. Freeze the sample to a committed artifact before searching it. The shuffle is over the *current*
   candidate list, so a growing pool re-rolls the sample between invocations and a "re-run the same
   command" instruction does not reproduce the same experiment (ADR-076 decision 1).
4. Treat the re-run as a **second look** on a nested sample and read it under a pre-stated
   multiplicity boundary, since look 1's estimate and direction are known (ADR-076 decision 3).

## Why it belongs in the series

This is the fourth way this project's pre-stated criteria have failed for reasons unrelated to the
thing under test: ADR-063's first clause named cells with nothing to find; ADR-070's named a rate
whose SE was 3× any plausible effect; ADR-063's second named a quantity the gate produces once in
3,029; ADR-074's would have fired on the mean of the same numbers it read as a median. The new entry
is **"the sample was capped by an argument nobody checked."** The generalisation is the same one
each time: *before spending a pre-registered measurement, verify what its sample actually is.*

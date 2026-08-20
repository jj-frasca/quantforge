# ADR-062: The sharded hunt must read the pool it is adding to

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-046 (candidate-level trial accounting), ADR-026 (sharded discovery)
- **Relates to**: ADR-016 (DSR/MinTRL gate), ADR-030 (single writer for generated data)

## Context

ADR-046 defines `lifetime_trials` as the cumulative count of concrete hypotheses ever evaluated for
a symbol, and it is the denominator of both the deflated-Sharpe haircut and the MinTRL requirement.
`run_universe_hunt` computes it as `store.trials_for_symbol(symbol) + this run's candidates`, and
`_trials_for_symbol` takes the MAX across the symbol's stored experiments specifically so the count
survives pool pruning.

**In production that store is empty on every run.** `scripts/shard_hunt.py` builds
`JsonFileExperimentStore(Path(out_pool))`, and `daily-discovery.yml` passes
`$GITHUB_WORKSPACE/shard_N.json` — a path that does not exist when the job starts. The committed
pool at `data/research_pool/` is checked out in the same workspace and never read. So
`prior_trials` is 0 for every symbol on every daily run, and `lifetime_trials` is just that run's
candidate count.

The pool shows it directly: 64 of 607 symbols carry a **decrease** in `lifetime_trials` between
consecutive experiments (52 of them on 2026-08-19 alone), which is impossible under a cumulative
counter. `T`, `TXN`, `XOM`, `BAC`, `AMD` and `PEP` all went 140 → 35 overnight.

**The direction of the error is the one that matters.** A smaller denominator means a smaller
deflated-Sharpe haircut and a shorter required track record — the bar the project publishes as its
central honesty claim has been **easier** than stated. Nothing has graduated regardless, so no
promoted result is affected, but the gate has not been the gate that is documented.

## Decision

**Give the shard the committed pool as a read-only prior, and keep its own file as the only thing it
writes.**

1. `PriorAwareExperimentStore(writer, prior)` — `trials_for_symbol` returns the max of the two
   stores' counts, `add`/`all` touch only the writer. Both halves matter: reading the prior restores
   ADR-046's denominator, and writing only to the shard file preserves ADR-030's single-writer rule
   and ADR-026's race-free consolidation.
2. `shard_hunt.py` wraps its shard-file store with a `PartitionedExperimentStore` over
   `data/research_pool/` as the prior. That directory is already checked out in the shard's
   workspace, so this needs no workflow change and no extra I/O beyond the symbols it hunts.
3. **State the over-counting caveat where the number is defined, because it is real.** A daily hunt
   re-searches the SAME grid on one more day of data. Re-testing an existing hypothesis is not a new
   hypothesis, so a strictly cumulative count overstates selection breadth; the genuinely new
   hypotheses each day are the refined configurations, which depend on that day's winner. Counting
   every candidate every time is therefore an **upper bound** on breadth. This ADR takes the upper
   bound deliberately — a bar that is too high refuses a real edge, a bar that is too low
   manufactures one, and only the second is a claim the project would have to retract.

## Alternatives considered

- **Count distinct configurations ever evaluated.** The correct quantity, and rejected only because
  the pool stores one finalist per family rather than every candidate, so the set does not exist to
  be counted. Recording a hash set of evaluated configs per symbol would make it possible and is the
  natural follow-up if the upper bound ever becomes binding on a real graduate.
- **Treat each day's re-search as one sequential test and apply an alpha-spending correction.** The
  statistically precise treatment of repeated testing as data accrues, and much larger than this
  fix; it also needs a decision about what the spending function is. Recorded as future work rather
  than smuggled into a bug fix.
- **Point the shard's store at `data/research_pool/` for both reading and writing.** Rejected: ten
  parallel shards writing one directory is exactly the race ADR-026's consolidation step exists to
  avoid, and ADR-030 forbids the second writer.
- **Leave it and document the reset.** Rejected. The published claim is that selection breadth is
  priced into the bar; a denominator that resets nightly does not price it.

## Consequences

- The bar rises for every symbol that has been hunted before, which is nearly all of them — the DSR
  haircut and the MinTRL requirement both grow with the accumulated count. **Expect the funnel to
  get narrower, not wider.** That is the correction working.
- `PoolReport.n_trials` becomes a genuinely cumulative figure rather than a sum of per-run counts.
  The README's "227,000+ trials" was already the sum of the per-run values, so it does not overstate
  anything, but its meaning changes and it will grow faster.
- Existing pool rows keep their recorded values. The next run reads the max of them as its prior, so
  the count resumes from the highest value ever recorded rather than being retro-corrected — the
  conservative, non-rewriting choice, consistent with `_trials_for_symbol` surviving pruning.
- No calibration artifact is affected: `measure_power` and `calibrate_gate` deliberately take no
  store, so a planted or null symbol has never had a prior to carry.

## Reversal

Delete `PriorAwareExperimentStore` and the two lines in `shard_hunt.py` that build it. The pool's
recorded counts stay as they are; the next run simply stops carrying them forward again.

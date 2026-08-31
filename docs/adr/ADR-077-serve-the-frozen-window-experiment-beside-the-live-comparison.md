# ADR-077: Serve ADR-076's frozen result beside the live window comparison, from its artifact

- **Status**: Accepted
- **Date**: 2026-08-31
- **Deciders**: Autonomous session #17 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-076, whose measured answer exists in the repo but nowhere a reader of the
  dashboard can see it
- **Relates to**: ADR-074 (the panel and endpoint this extends), ADR-068 (the drift control being
  reported), ADR-067 (null means *not measured*), ADR-030 (one writer per generated file)

## Context

`GET /api/v1/window-comparison` computes `compare_search_windows` over the partitioned pool and the
dashboard renders it in `WindowComparisonPanel`. The panel's first row is **the criterion** — the
drift-controlled excess delta — and over the pool alone it is `null`, which the panel renders as:

> **Not measured** — the rows searched before ADR-063 predate the paired benchmark, so their drift
> cannot be removed

Measured against the pool today: `n_symbols = 368`, **`excess_n = 0`**, `oos_delta = -0.038
[-0.060, -0.009]`.

That sentence was true when ADR-074 wrote it and it is **false now**. ADR-076 measured exactly that
quantity on 2026-08-31 — `-0.008 [-0.055, +0.022]` at the Pocock two-look boundary over a frozen
200-symbol sample — and the result is committed at `data/window_experiment/adr076_summary.json`. The
dashboard therefore reports "not measured" about the one question three sessions of this project
were spent answering, while displaying beside it the surrogate number that ADR-076 has just shown
does not survive the control.

`excess_n` over the pool will also never stop being 0. The pool's short-window rows were searched
before ADR-068 existed and carry no `walk_forward_hold_sharpe`; production `SEARCH_HISTORY_START` is
1990, so the daily discovery only ever adds long-window rows. The only rows that carry the benchmark
at the short window are the ones ADR-076's experiment created, and those raw stores are gitignored
(~1 MB each, refused by the 500 KB pre-commit hook). **Waiting does not fix this. Nothing in the
production pipeline will ever fill that row.**

## Decision

1. **Serve the ADR-076 result from its committed summary artifact, never by recomputation.** A new
   read-only endpoint `GET /api/v1/window-experiment` returns the contents of
   `adr076_summary.json`, or `null` when the file is absent. Recomputing it at request time would
   re-open a sequential test that ADR-076 decision 3 closed at look 2 of 2: the sample would silently
   grow with the pool and every page load would be another look. **The frozen artifact is the
   result. The endpoint is a reader, not an estimator.**

2. **It is a separate endpoint and a separate block in the panel, not extra fields on the live
   comparison.** The two are over different samples — the live surrogate over 368 pool symbols, the
   criterion over ADR-076's frozen 200 — and merging them into one object invites exactly the
   comparison a reader should not make. The live table keeps its "not measured" row, with its copy
   changed to point at the frozen result below it rather than to imply nobody has looked.

3. **The served object carries its own `alpha` and `n`, and the panel prints both.** The criterion
   interval is at nominal two-sided alpha = 0.0294, not 95%. A band rendered beside three 95% bands
   with no label is a wrong comparison presented as a right one. The look-1-alpha reading travels
   with it and is labelled as continuity only, exactly as the driver prints it.

4. **The panel states that the sequence is closed.** The result is not a statistic that will improve
   with more data; it is a spent pre-registration. The reader is told that, so nobody — including a
   future session — reads a stale-looking null as an invitation to run it again. Extending it needs
   a new ADR with a three-look boundary.

5. **Absent file reads as "not measured", never as zero** (ADR-067). The endpoint returns `null` and
   the panel says the experiment has not been run, which is the honest rendering for a checkout that
   has not fetched the artifact.

## Alternatives considered

1. **Recompute from the raw shard stores at request time.** Rejected twice over: the stores are
   gitignored, so a deployed backend does not have them; and it re-opens the closed sequence, which
   is the one thing ADR-076 spent a boundary to prevent.
2. **Commit the raw stores so the endpoint can recompute.** Rejected: ~1 MB each against a 500 KB
   pre-commit limit, and it still re-opens the sequence.
3. **Merge the experiment's rows into `data/research_pool/`.** Rejected hardest. It violates ADR-030
   (the daily discovery is that directory's writer), and it would contaminate *every other* pool
   statistic — DSR denominators, the null comparison, the leaderboard — with rows searched at a
   non-production window. The window experiment is deliberately outside the pool.
4. **Add the fields to the existing `WindowComparison` response.** Rejected under decision 2: one
   object over two samples at two alphas is a presentation that produces wrong readings.
5. **Do nothing; leave the dashboard saying "not measured".** Rejected: it is a false statement about
   the project's own central result, on the artifact this project exists to be judged by.

## Consequences

- The dashboard reports the answer to ADR-063's second clause instead of denying one exists, and
  reports it with the sample, the alpha and the closed-sequence status attached.
- `adr076_summary.json` acquires a consumer, which means its schema is now load-bearing. It is
  written by `scripts/window_experiment.py report` and by nothing else (ADR-030).
- The endpoint is the first in this API to serve a *frozen* result rather than a live derivation.
  That distinction is the point, and the panel says so in words rather than leaving it to be
  inferred from a timestamp.

## Reversal

Delete the endpoint, its response model, the frontend hook and the panel block, and restore the
live table's original "not measured" copy. `adr076_summary.json` stays on disk either way — it is
ADR-076's evidence, not this ADR's. Nothing else reads it, and no threshold, gate or graduation
decision depends on any of it.

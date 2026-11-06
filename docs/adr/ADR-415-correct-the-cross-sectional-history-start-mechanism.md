# ADR-415: Correct ADR-414's mechanism — a universe file does not extend fetched history

- **Status:** Accepted
- **Date:** 2026-11-06
- **Deciders:** Interactive session (Joe present), same session as ADR-414
- **Corrects:** ADR-414
- **Relates to:** FINDING-350

## Context

ADR-414 shipped `data/universes/large_cap_longhistory.txt` (235 symbols independently verified to
have real price data in Q1 1990) on the theory that the cross-sectional panel's `RECENT_HISTORY_
START` (2005-01-01) floor was being forced by 14 younger members of `large_cap.txt`, and that
pointing the hunt at an all-old-enough universe would let the panel's common window extend back to
1990, closing (or at least narrowing) the MinTRL gap FINDING-350 measured.

**That ADR claimed "No code changes" — that claim was wrong, and this session's own dispatch
proved it wrong before anyone else had to.** `scripts/cross_sectional_hunt.py`'s `dataset_provider`
passes the constant `RECENT_HISTORY_START` to `fetch_research_dataset` as the fetch start for
*every* symbol, completely independent of which universe file supplied those symbols. The universe
file controls *which* symbols are hunted; it has no mechanism to control *how far back* their
price history is requested. Dispatching with the new universe (`gh workflow run cross-sectional-
hunt.yml -f universe=data/universes/large_cap_longhistory.txt`, run `42170667294`) produced a real
result — `xs_quality` won again (12/12 now), `panel_manifest` start date still `2005-01-01`,
observed Sharpe 0.56 (down from the 0.96 peak), deflated Sharpe −1.77, still blocked by the same
`dsr_ok`/`mintrl_ok` pair. **That run tested "235 symbols from 2005" against the earlier 51-symbol
runs, not "more history" against anything.** The lower Sharpe is plausibly just a broader, noisier
cross-sectional slice and says nothing about whether extending history would help — the panel
genuinely never got longer. This result must not be read as evidence against the history-extension
hypothesis; it is not a measurement of that hypothesis at all.

## Decision

Add the missing mechanism, narrowly:

1. `scripts/cross_sectional_hunt.py` gains `_resolve_history_start(env: Mapping[str, str]) ->
   datetime`: reads `HISTORY_START` (an ISO date string) from the given environment mapping,
   defaulting to the unchanged `RECENT_HISTORY_START` when the variable is unset or empty, and
   raising on an unparseable value (fail loud on a typo'd dispatch input, not silently default).
   `main()` calls it with `os.environ` and threads the result into `dataset_provider` in place of
   the bare constant.
2. `cross-sectional-hunt.yml` gains a second `workflow_dispatch` input, `history_start` (optional,
   default empty string = unchanged default behavior), passed through as the `HISTORY_START` env
   var alongside the existing `universe` input.
3. **The scheduled (non-dispatch) trigger is completely unaffected.** `HISTORY_START` is empty on
   every `schedule`-triggered run, `_resolve_history_start` returns the unchanged
   `RECENT_HISTORY_START`, and every other consumer of that constant (paper book, broker, forward
   scoring) is untouched — this ADR adds an override to one script's one non-default dispatch
   path, exactly mirroring how `universe` already works on the same workflow.

With this in place, the actual test ADR-414 intended is: dispatch with BOTH
`universe=data/universes/large_cap_longhistory.txt` AND `history_start=1990-01-01`. That dispatch
is queued immediately following this commit; its result gets its own dated addendum to
FINDING-350, reported honestly whichever way it comes out — same discipline ADR-414 already
committed to.

## What this is NOT

- Not a second attempt to weaken DSR/PBO/MinTRL. Same unmodified gate.
- Not a change to `RECENT_HISTORY_START` itself. Still the default for every untouched caller.
- Not a retraction of FINDING-350's measurement (the 11/17.5y-margin numbers from the original
  51-symbol, 2005-start panel) — that measurement is real and unaffected by this correction. Only
  ADR-414's proposed FIX was incomplete; the finding it was responding to was not.

## How to reverse

Remove `_resolve_history_start`, revert `dataset_provider` to the bare `RECENT_HISTORY_START`
constant, and remove the `history_start` workflow input. The scheduled trigger's behavior is
identical either way, so reversing this is a no-op for anything except a future explicit dispatch.

## Retro

The error was concrete and avoidable: ADR-414 verified symbol-level data availability carefully
(live-queried, cross-checked, CSCO caught) but never traced the actual fetch call in
`cross_sectional_hunt.py` to confirm the universe file's symbols would reach a longer window — it
inferred the mechanism from the *reason* `RECENT_HISTORY_START`'s own comment gave ("bounded by its
newest member") without checking that reason was the *only* thing standing between the universe and
a longer panel. The fix: before shipping a data-availability-only change as a one-file, no-code-
change ADR, trace the one call site that actually consumes the new data, the same way this session
traced `minbtl_years` and `split_panel_holdout` before trusting FINDING-350's own numbers.

# ADR-023: Value pre-screen into the hunt — combine the algo with undervalued companies

- **Status**: Accepted
- **Date**: 2026-07-09
- **Deciders**: Joe Frasca
- **Implements**: mission north star (DELEGATION.md WP-H) — combine the technical algo with
  *genuinely undervalued* companies, and record each candidate's valuation so we can later measure
  whether value+algo survivors outperform.
- **Builds on**: ADR-022 (value research engine: `score_valuation` → `UndervaluationScore`,
  `price_join`, `SecEdgarFundamentalsSource.fetch_history`), ADR-017 (fundamentals veto),
  ADR-014/015/016 (the lab, the versioned `GateConfig`, the experiment store).

## Context
The value engine (ADR-022) is merged but **unwired** — nothing in the hunt consumes it. Joe's core
want is to *combine the algo with undervalued companies*, not run two disconnected screens. There
are two distinct moves, and they must be separable:

1. **Value pre-screen** — before spending a per-symbol network + compute budget hunting a name,
   skip names that don't even *look* undervalued. This narrows the universe toward the intersection
   Joe cares about (cheap ∩ technically-sound).
2. **Record the valuation** — attach each hunted candidate's `UndervaluationScore` to its
   `Experiment`, so the pool carries the value axis next to the technical verdict. Only by recording
   it can we later ask "did the value+algo survivors actually outperform the algo-only ones?"

Three forces shape the decision:
- **Overfitting can sneak in here.** A hardcoded value threshold, silently tuned until the hunt
  "finds winners", is exactly the multiple-comparisons trap the lab exists to resist. The screen
  must be a **tunable, versioned config** (like `GateConfig`), recorded with the run, calibrated
  deliberately — never a magic constant buried in code.
- **A screen that's too tight starves graduation.** If the pre-screen removes so many names that
  the cross-symbol hunt has nothing left, we've traded one bias for another (and universe-level
  deflation, ADR-018, gets weaker with fewer shots). The screen must default **OFF**, and when ON
  it must lean permissive.
- **Not every name has fundamentals.** ETFs file no 10-K, and some tickers don't resolve to a CIK.
  The existing fundamentals veto (ADR-017) already handles this by falling back to *technicals
  only*. The value pre-screen must do the same — never veto a name merely because it can't be
  scored.

## Options Considered
1. **Hardcode a value cutoff inside `run_universe_hunt`.**
   - Pro: least code.
   - Con: violates ADR-015's "no hardcoded thresholds" — un-versioned, un-recorded, and the fastest
     way to overfit the universe selection. Rejected.
2. **Make valuation a *graduation* veto inside `run_search` (like the fundamentals veto).**
   - Pro: symmetric with ADR-017.
   - Con: (a) it would require editing `run_search` (owned by another slice), (b) it wastes the full
     hunt budget on names we already know aren't cheap, and (c) conflating "is it cheap" with "does
     the strategy graduate" muddies two independent questions. We want the value axis *recorded*
     next to every candidate, not used to silently kill graduates. Rejected as the primary
     mechanism.
3. **A tunable, versioned pre-screen + record-on-experiment, both OFF by default, both injectable
   (chosen).**
   - Pro: honest (versioned config, recorded per run), cheap (skips non-cheap names before the
     hunt spends its budget), separable (pre-screen and recording each toggle independently),
     backward-compatible (existing hunt/tests unchanged when value is off), and testable without
     network (the score provider is injected).
   - Con: two new knobs to calibrate; the pre-screen and the recording are wired in `universe.py`
     rather than the per-symbol `search.py`, so a caller who bypasses `run_universe_hunt` gets
     neither. Acceptable — the universe hunt is the mission's entry point.

## Decision
Add a new **`backend/app/research/lab/value_filter.py`** and wire an **optional** value gate into
`run_universe_hunt`. Nothing about the existing hunt changes when value is disabled (the default).

- **`ValueGateConfig`** — a frozen, versioned Pydantic config mirroring `GateConfig`:
  - `min_score: float = 0.5` — keep a name only if its `UndervaluationScore.score` (0–1, higher =
    cheaper vs its own P/E and P/S history + DCF margin of safety) is **≥** this. **Threshold
    semantics:** the score is a *cheapness* score, so higher passes. `0.5` is the neutral midpoint —
    "at least as cheap as the middle of its own historical multiples distribution" — chosen as a
    permissive starting point that keeps roughly the cheaper half of a broad universe rather than a
    handful of names. It is a **calibration knob**, expected to be tuned per hunt like `GateConfig`,
    not a proven constant.
  - `keep_unscored: bool = True` — a name we cannot score (ETF / no CIK / no computable components)
    **passes** the pre-screen and is hunted on technicals only. This is the ADR-017 fallback,
    generalized. Set `False` for a stricter "fundamentals-required" universe.
  - `require_margin_of_safety: bool = False` — optional stricter gate: also require a positive DCF
    margin of safety. Off by default because the DCF is the most assumption-laden signal (ADR-022).
  - `version_hash` property (SHA over `model_dump()`, same mechanism as `GateConfig`) so a run is
    reproducible against the exact rubric that filtered it.
- **`ValueScreen`** — a frozen result: `passed: bool`, the `score` it was judged on (or None), and a
  `reasons` list per failed check. Honest per rule 6 — it flags a name as *potentially* (not)
  undervalued.
- **`screen_value(score: UndervaluationScore | None, config) -> ValueScreen`** — the pure decision.
  `None` score (or a score object whose `.score` is None) routes through `keep_unscored`.
- **`make_value_provider(history_provider, price_series_provider, *, assumptions=None)`** — composes
  the ADR-022 contract into a per-symbol `Callable[[str], UndervaluationScore | None]`:
  `history = history_provider(symbol)` → `attach_fiscal_year_prices(history, closes)` →
  `score_valuation(joined, current_price)`, where `current_price` is the last close and each fiscal
  year is priced via `price_join`. Both providers are **injected**, so unit tests use fakes (no
  network in CI) and a `@pytest.mark.live` test wires `SecEdgarFundamentalsSource.fetch_history` +
  a real price series. A `history_provider` that raises (ETF / unmapped ticker) → `None` (unscored).
- **`run_universe_hunt`** gains two optional params — `value_provider` and `value_config` — both
  `None` by default. When both are set, for each symbol it computes the score, screens it, and:
  - **fails the pre-screen** → the symbol is skipped (not hunted) and recorded in a new
    `UniverseHuntResult.filtered: dict[str, str]` (symbol → reasons). It never becomes an
    `Experiment` and never touches the network-heavy search.
  - **passes** → the hunt runs as before, and the resulting `Experiment` is stamped with the
    `UndervaluationScore` via `model_copy` (so `search.py` is untouched — file ownership respected).
- **`Experiment`** gains one optional field, `undervaluation_score: UndervaluationScore | None =
  None`. Default `None` keeps every existing experiment, store round-trip, and test valid.

## Consequences
- The mission's entry point can now hunt the **cheap ∩ technically-sound** intersection, with the
  value axis recorded alongside every candidate — enabling the later "do value+algo survivors
  outperform?" analysis (a follow-on, not this slice).
- **Backward-compatible by construction**: value off = the current hunt, byte-for-byte. Every
  existing universe test passes unchanged.
- **Honest & reproducible**: the screen is versioned and recorded; the config's `version_hash`
  distinguishes runs; rule-6 language throughout ("potentially undervalued").
- **Starvation guard**: OFF by default, a permissive `min_score` default, and `keep_unscored=True`
  so ETFs/unmapped names are never vetoed — the screen narrows, it does not empty, the universe.
- **Deferred**: using valuation as a graduation veto or a live *signal* inside the backtest;
  peer-relative cheapness; a frontend surface for the recorded score (WP-I). This slice ships the
  pre-screen + recording only.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*

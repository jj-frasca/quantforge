# ADR-012: Surface regime-breakdown in ValidationReport

- **Status**: Accepted
- **Date**: 2026-06-19
- **Deciders**: Joe Frasca

## Context
`backend/app/validation/regime_analysis.py` implements `analyze_regimes()` — bucketing
a strategy's bars into "bull" / "bear" by the sign of the market's trailing 20-bar
return and reporting (n_bars, total_return, Sharpe) per regime. This is one of the
fragility checks called out in validation-methodology.md §5: a strategy whose edge
lives entirely in one regime is fragile, and the UI should make that visible.

But `analyze_regimes()` is dead code — nothing calls it. The Validation page renders
PBO / Deflated Sharpe / parameter stability / fold counts, with no regime breakdown.
That's a real gap: a methodology module exists in the repo but doesn't reach the user.

There are two questions to settle: (1) where the regime breakdown belongs (separate
endpoint or extension of the existing `/validate` response), and (2) whether to use
the existing 20-bar trailing window or expose it as a tunable.

## Options Considered

1. **New `POST /api/v1/regime-analysis` endpoint**, returned alongside but separately.
   - Pro: cleanly factored; regime analysis is conceptually distinct from PBO+DSR.
   - Con: forces the frontend to fire two requests for one user action ("run validation"),
     adds a new contract to maintain, and creates an off-by-one timing where the
     validation verdict can render before the regime breakdown lands. Duplicates the
     data-fetching path. /validate already has the (strategy, dates, data) the regime
     check needs — no reason for a separate roundtrip.

2. **Extend the `/validate` response** with a `regime_breakdown` field; the engine
   calls `analyze_regimes()` after the per-config backtests and serializes the result
   for the BEST config (the one whose Sharpe drove the report's headline metrics).
   - Pro: one request, one response, one piece of UI to add. Aligns with the existing
     ValidationReport pattern (a single object summarizing the whole run). The best
     config is the right scope because the rest of the report is also about that
     config — keeping the regime breakdown on the same scope means the user reads it
     as "this config that you'd be tempted to deploy actually only works in bulls."
   - Con: makes the response larger; the schema now carries an inner map. Couples
     regime analysis to the validation suite (you can't run regime analysis without
     running PBO etc).

3. **Run regime analysis on EVERY config and report all of them.**
   - Pro: lets the user see whether SOME config is regime-robust even when the best
     one isn't. More information.
   - Con: explodes the response payload, blurs the report's narrative (which is
     "the best config you'd deploy — does it survive?"), and the marginal info beyond
     the best config is usually low (the configs are siblings with similar edges).
     Premature; can be added later if anyone asks for it.

For the window question: `analyze_regimes()` defaults to a 20-bar trailing window;
that's a reasonable default for daily data and is what the methodology doc cites.
There is no user-facing reason to expose it as a tunable in the MVP — adding it
to the form adds noise and the gain is small.

## Decision

Take option 2 with the default 20-bar window. The validation engine, after picking
the best config (`best = argmax(sharpes)`), will call `analyze_regimes(best_returns,
data['close'])` and attach the resulting `dict[str, RegimeMetrics]` to the report as
a new `regime_breakdown` field. The frontend renders the breakdown as a small table
or set of stats below the headline metrics; if both regimes have data, the page
explicitly names the gap ("only works in bulls" / "robust across regimes").

The contract:
- `ValidationReport.regime_breakdown: dict[str, RegimeBreakdownEntry]` where
  `RegimeBreakdownEntry = {n_bars: int, total_return: float, sharpe: float}`.
- Keys are `"bull"` and `"bear"`; missing key means no bars in that regime (the
  frontend must handle this — extremely short windows can be all-bull).

## Consequences

What becomes easier:
- One user action ("Run validation") returns one self-contained report with all
  the fragility signals on it. Matches the project's "honesty in UI" rule
  (rules/frontend-typescript.md): a failing report shows ALL the reasons.
- The regime-analysis module is no longer dead code.

What becomes harder / new obligations:
- The `/validate` Pydantic response schema is now larger; any future change to
  `RegimeBreakdownEntry` is a breaking response change and needs the matching Zod
  schema update — already a [[feedback-frontend-shadow-validators]] pitfall.
- Validation engine now needs the price series, not just the returns. Already
  threaded through `data: pd.DataFrame`; no shape change, just a new read.
- Regime is bull/bear today; if the methodology grows a third regime ("sideways")
  the API contract must extend cleanly. Keeping the field as a dict (open set of
  keys) rather than a fixed `bull: ..., bear: ...` object means the schema accepts
  new regimes without a contract break.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*

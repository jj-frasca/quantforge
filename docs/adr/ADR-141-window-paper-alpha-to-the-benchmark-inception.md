# ADR-141: Measure paper-book alpha over the benchmark's own window, not the nominal $100k start

- **Status:** Accepted
- **Date:** 2026-09-27
- **Deciders:** Autonomous session 122 under `.claude/AUTONOMY_CHARTER.md`
- **Resolves:** FINDING-072
- **Extends:** the alpha tracking introduced in the commit "track the paper book's alpha vs SPY,
  not just absolute return"

## Context

`append_equity_point` computes `alpha_since_start = return_since_start - benchmark_return`, where
`return_since_start` is the book's return against a fixed nominal constant (`$100,000`) and
`benchmark_return` is SPY's return from the first-ever recorded equity snapshot's timestamp to now
(`paper_broker.py`'s `inception = history[0].timestamp`). The book's real equity at that first
snapshot was `$92,488.99`, not `$100,000` — trading had already happened before this tracking
series began. Because `return_since_start` never resets to the book's actual state at the
benchmark's own inception point, that pre-tracking gap is permanently subtracted into every
`alpha_since_start`, overstating the book's underperformance vs. the benchmark by a fixed amount
that has nothing to do with anything measured since inception (FINDING-072: ~7 points at the time
of writing).

## Options Considered

1. **Window the book's own return to the benchmark's inception point (`history[0].equity`), and
   subtract the benchmark return from that.**
   - Pro: apples-to-apples — both terms of the subtraction cover the identical [inception, now]
     window, which is the entire point of an excess-return statistic.
   - Pro: `return_since_start` (vs. the nominal $100k) is untouched and stays honestly labeled as
     the separate thing it already claims to be.
   - Con: `alpha_since_start` and `return_since_start` are no longer trivially related by
     `alpha = return_since_start - benchmark_return`; a reader must know they use different
     baselines. Mitigated by tightening the field's docstring.
2. **Rebase `return_since_start` itself onto `history[0].equity` instead of the nominal $100k.**
   - Pro: keeps the trivial `alpha = return_since_start - benchmark_return` relationship.
   - Con: destroys the honestly distinct "are we up on the $100k of paper capital we actually
     started with" question the field is documented and displayed (`EquityCurvePanel.tsx`,
     "since $100k start") to answer. Two real questions ("vs. nominal capital" and "vs. the
     market") would collapse into one, and the dashboard's own unaffected, correct label would go
     stale.
3. **Backfill/rewrite historical `alpha_since_start` values in `data/equity_curve.json` under the
   corrected formula.**
   - Pro: every historical point would read consistently.
   - Con: rewrites committed data-file history, which this project treats as an append-only
     experimental record; also requires re-deriving historical SPY prices for points where the
     benchmark was never fetched at all (pre-2026-08-19), which cannot be done honestly after the
     fact for points where `benchmark_return_since_start` was `None` by design.

## Decision

Option 1. `append_equity_point` computes the book's own return over the same window as
`benchmark_return` — from `history[0].equity` (or, when `history` is empty, the current point's own
equity, i.e. a zero-length window) to the current equity — and derives `alpha_since_start` from
that windowed return, not from `return_since_start`. `return_since_start` keeps computing against
the nominal `starting_equity` exactly as before; it is a different, still-honest question and nothing
in this ADR changes its value or its display. No historical `data/equity_curve.json` entries are
rewritten — they remain the honest record of what was computed and reported at the time, under the
formula that produced them; only appends made after this fix use the corrected calculation.

## Consequences

- `alpha_since_start` for every future snapshot compares the book and the benchmark over the
  identical window, closing the ~7-point-and-growing systematic overstatement FINDING-072 measured.
- `return_since_start` (displayed on the "Live" dashboard as "since $100k start") is unaffected —
  verified unchanged by the accompanying test suite.
- Historical `alpha_since_start` values already in `data/equity_curve.json` remain computed under
  the old formula; anyone diffing the series across this commit's deploy date should expect a level
  shift in `alpha_since_start` (not in `equity`, `return_since_start`, or `benchmark_return_since_start`)
  that reflects the fix, not a change in the book's actual performance.
- `EquityPoint`'s docstring and the comment above `benchmark_return_since_start` are corrected to
  describe the windowed calculation actually performed.

## Reversal

Revert `append_equity_point` to derive `alpha` from `return_since_start` directly. Not recommended:
that is exactly the conflation this ADR closes, and reintroduces a fixed, growing, unexplained bias
into the project's own stated "only honest" performance question.

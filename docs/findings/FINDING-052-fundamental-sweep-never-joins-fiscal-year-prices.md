# FINDING-052: Fundamental sweep never joins prices onto fiscal years, killing 2 of 3 value legs

- **Severity:** High
- **Status:** Resolved by ADR-124
- **Found:** 2026-09-24, autonomous session 104 (background audit of
  `backend/app/research/valuation/`, cold since 2026-07-09)
- **Affects:** `backend/scripts/fundamental_sweep.py` (ADR-029 Layer 3, the sole writer of
  `data/fundamentals_pool.json` per ADR-030)

## Finding

`UndervaluationScore` (ADR-022) blends three components: the current P/E ranked against the
company's own historical P/E distribution, the same for P/S, and the DCF margin of safety.
`compute_multiples` (`app/research/valuation/multiples.py`) builds those historical distributions
from `history.years`, filtering on `y.price is not None` — each year's `price` is populated only by
`attach_fiscal_year_prices` (`app/research/valuation/price_join.py`), which joins a market-price
series onto each fiscal year's `period_end`.

`fundamental_sweep.py`'s `main()` never called `attach_fiscal_year_prices`. It fetched only the
single most-recent close (`_latest_price`, a 14-day lookback window) and passed that float straight
into `compute_fundamental_record(history, price, sic)` — `history` itself unchanged, every year's
`price` field still `None`. Consequently `pe_hist`/`ps_hist` were always empty lists for every
company the sweep ever scored, `pe_percentile`/`ps_percentile` were always `None`, and the flags
list always carried `"insufficient P/E history for a percentile"` /
`"insufficient P/S history for a percentile"` — regardless of how many years of real fundamentals
history EDGAR actually returned. `value_score` in production was therefore always just the DCF
margin-of-safety component (or `None`), never the documented three-way blend.

This is production wiring drift, not a defect in the pure scoring functions — `score.py`,
`multiples.py`, and `price_join.py` are all correct and already well-tested in isolation (confirmed
during this audit). The correct composition pattern already exists elsewhere in the codebase:
`app/research/lab/value_filter.py`'s `make_value_provider` fetches a price series, calls
`attach_fiscal_year_prices`, and only then scores — `fundamental_sweep.py` simply never adopted that
pattern when it was written (ADR-029, 2026-08-18).

The gap was invisible in tests: `test_fundamental_record.py::test_compute_with_price_adds_value_and_
combined` passed a history with no `eps`/`price` set on any year and only asserted "value may or may
not be computable" — it never checked that `pe_percentile`/`ps_percentile` populate when a full,
properly-joined price history is actually supplied, so a change (or a wiring gap) in that path
wouldn't have been caught.

Since `value_score`/`combined_score` feed both the ADR-029 fundamental leaderboard and the
cross-sectional hunt's value leg (`score_maps`), this silently weakened two-thirds of the intended
"genuinely good, reasonably priced companies" signal in the pipeline that actually gates which
symbols look cheap — for the entire life of the sweep (since ADR-029, 2026-08-18) until this fix.

## Reproduction

```python
# fundamental_sweep.py's pre-fix call shape, reproduced directly:
from app.research.fundamentals.record import compute_fundamental_record
# `history` from edgar.fetch_history(symbol) — every year's `price` is None (EDGAR carries no prices)
rec = compute_fundamental_record(history, price=latest_close)  # price is a single float, not joined
# rec.flags always contains "insufficient P/E history for a percentile" and
# "insufficient P/S history for a percentile", regardless of history.years' actual length.
```

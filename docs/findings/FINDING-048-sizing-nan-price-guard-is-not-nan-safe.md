# FINDING-048: Sizing's non-positive-price guard is not NaN-safe

- **Severity:** Medium
- **Status:** Resolved by ADR-120
- **Found:** 2026-09-23/24, autonomous session 104
- **Affects:** `app.execution.sizing.equal_weight_targets`

## Finding

`equal_weight_targets` computes its active-name count with `q.price > 0.0` but skips a quote to a
flat (zero) target with `q.price <= 0.0`. Both comparisons evaluate to `False` for `price = nan`
(IEEE 754: every ordered comparison against NaN is `False`), so a NaN-priced quote is excluded from
the active-count denominator but is **not** caught by the per-quote flat guard. Execution falls
through to `int(target_dollars / q.price)`, which raises `ValueError: cannot convert float NaN to
integer` for that one bad quote — aborting the whole `equal_weight_targets` call (every symbol in
the book, not just the bad one), since it returns a single list rather than yielding per-symbol.

`PriceBar` ingestion already rejects NaN/Inf, so a `quote_position`-built quote sourced from stored
bars should not carry NaN today. But `PositionQuote`/`equal_weight_targets` is a public, directly
callable pure-math contract (no dependency on ingestion having run), and the function's own
docstring already promises "a non-positive price yields a 0 target" — NaN is neither positive nor
negative, so it should fall under that same promise instead of raising.

## Reproduction

```python
from app.execution.sizing import PositionQuote, equal_weight_targets

equal_weight_targets(
    [
        PositionQuote(symbol="AAPL", signal=1.0, price=100.0),
        PositionQuote(symbol="MSFT", signal=1.0, price=float("nan")),
    ],
    equity=10_000.0,
)
# ValueError: cannot convert float NaN to integer
```

# FINDING-053: Strategy-builder smoke test silently stopped covering new strategies

- **Severity:** Low
- **Status:** Resolved by ADR-125
- **Found:** 2026-09-24, autonomous session 104 (background audit of `backend/app/research/
  strategies/{base,builder,catalog,configs}.py`, `base.py` cold since 2026-05-28)
- **Affects:** `backend/tests/unit/test_strategy_builder.py::
  test_build_strategy_dispatches_each_config_variant`

## Finding

`test_build_strategy_dispatches_each_config_variant`'s own comment states its purpose: "every
catalog discriminator can be constructed via `build_strategy`. Any missing branch here is the
moment ADR-010's promise breaks for /validate." Its body was a hardcoded literal list of 11
`StrategyConfig` instances — last touched in the "Triple MA Alignment" commit (2026-06-06), the 11th
strategy added to the catalog. 23 more strategies have been added since (`STRATEGY_CATALOG` now has
34 entries) without this test's list growing, so it silently stopped exercising 23 of
`build_strategy`'s isinstance branches while its own comment kept claiming to be the backstop for
exactly that regression.

Not an active coverage gap in practice — `grid_generator`'s tests exercise every catalog entry
through the same dispatch table indirectly (confirmed: `test_grid_generator.py` iterates
`STRATEGY_CATALOG` for every entry). But a test whose stated intent no longer matches its content is
exactly the kind of drift that misleads whoever next debugs a real builder regression and trusts
this test's name/comment to mean what it says.

## Reproduction

```python
from app.research.strategies.catalog import STRATEGY_CATALOG
# 34 entries as of 2026-09-24; the pre-fix test's hardcoded list covered only the first 11 added.
len(STRATEGY_CATALOG)  # 34
```

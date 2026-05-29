# Data Contracts (Cold Memory)

Formal schemas, storage DDL, and query rules for the data layer. Self-contained: read this
when working on `backend/app/data/`. Behavioral rules live in CLAUDE.md; domain heuristics in
the `data-engineer` agent. This doc holds the schemas, SQL, and check definitions.

Authoritative decisions: ADR-003 (TimescaleDB), ADR-004 (canonical PriceBar, normalize at
ingestion), ADR-005 (DataSourceAdapter), ADR-006 (quality gate).

---

## 1. `source` enum

```
Source = Literal["yfinance", "polygon"]
```
yfinance is primary (no key). Polygon is added in Phase 3 (enables vendor cross-validation).

---

## 2. PriceBar (canonical OHLCV bar)

Pydantic v2 model in `app/data/models/price_bar.py`. One row = one symbol's bar for one
timestamp from one source. Already split/dividend-adjusted at ingestion (ADR-004).

| Field | Type | Constraints / Notes |
|---|---|---|
| `symbol` | `str` | uppercased, non-empty, stripped |
| `timestamp_utc` | `datetime` | **tz-aware, UTC**. Naive → `ValidationError`; aware non-UTC → converted to UTC |
| `open` | `Decimal` | finite, > 0 |
| `high` | `Decimal` | finite, > 0; `high >= max(open, close, low)` |
| `low` | `Decimal` | finite, > 0; `low <= min(open, close, high)` |
| `close` | `Decimal` | finite, > 0 |
| `volume` | `int` | >= 0 |
| `adj_factor` | `Decimal` | finite, > 0. Cumulative split/dividend factor **already applied** to OHLC |
| `source` | `Source` | `"yfinance" \| "polygon"` |
| `quality_flags` | `dict \| None` | `None` means clean (no issues). Populated by the quality gate |

**Decimal precision**: stored as `NUMERIC(18,6)` (price), `NUMERIC(10,6)` (adj_factor). Use
`Decimal`, never `float`, so values round-trip exactly.

**adj_factor invariant**: applied exactly once, at ingestion. Re-applying downstream yields
prices that are `adj_factor`× wrong — a bug, not a feature.

**Validation rules (enforced in the model)**:
1. `timestamp_utc` tz handling above (UTC coercion — ADR-006; this is enforced, not flagged).
2. all four prices finite and > 0 (§8 invariant #1).
3. OHLC ordering: `low <= open,close <= high` and `low <= high`.
4. `volume >= 0`; `adj_factor > 0`.

---

## 3. FundamentalData

Pydantic model in `app/data/models/fundamental_data.py`. Point-in-time fundamentals.

| Field | Type | Notes |
|---|---|---|
| `symbol` | `str` | uppercased |
| `report_date` | `date` | the fundamentals' as-of date |
| `pe_ratio` | `Decimal \| None` | may be null (e.g. negative earnings) |
| `pb_ratio` | `Decimal \| None` | |
| `ps_ratio` | `Decimal \| None` | |
| `ev_ebitda` | `Decimal \| None` | |
| `revenue` | `Decimal \| None` | currency units |
| `net_income` | `Decimal \| None` | may be negative |
| `market_cap` | `Decimal \| None` | > 0 when present |
| `sector` | `str \| None` | |
| `industry` | `str \| None` | |
| `source` | `Source` | |

Ratios are nullable on purpose — missing/undefined is common and must not be coerced to 0.

---

## 4. Data quality models

`app/data/models/quality.py`.

```
class DataQualityIssue:
    check: str          # check identifier, e.g. "missing_bars"
    severity: Literal["info", "warning", "error"]
    message: str        # "flags potential X ..." — never "prevents/guarantees"
    context: dict | None # offending values, dates, thresholds

class DataQualityReport:
    symbol: str
    checked_at: datetime          # tz-aware UTC
    issues: list[DataQualityIssue]
    passed: bool                  # downstream MUST verify passed is True (ADR-006)
```
`passed` is `False` if any issue has severity `"error"`. `warning`/`info` do not fail the gate
but are recorded. Wording is always "flags potential X" (CLAUDE.md rule 6).

---

## 5. The 8 quality checks (formal definitions)

Run by `DataQualityEngine` (`app/data/quality/`). All thresholds are configurable; defaults
shown. Checks FLAG potential issues — they do not guarantee correctness.

> **Build status:** implemented today = #1 survivorship (info), #2 split/dividend, #4
> missing_bars, #5 price_anomaly, #6 stale_data (warnings), plus an `insufficient_data` error;
> #7 timezone is enforced at the PriceBar boundary. **NOT yet implemented:** #3 corporate_action
> and #8 vendor_cross_validation (the latter needs the Polygon adapter, Phase 3+). See
> ARCHITECTURE.md §0.6.

| # | Check id | What it flags | Default threshold | Severity |
|---|---|---|---|---|
| 1 | `survivorship_risk` | universe may exclude delisted symbols — **risk flag only, not solved** | n/a (always informational when universe is yfinance-sourced) | info |
| 2 | `split_dividend_consistency` | implausible `adj_factor` jump between consecutive bars | factor ratio outside [0.5, 2.0] step | warning |
| 3 | `corporate_action` | price discontinuity suggesting delisting/merger/remap | gap > 50% not explained by adj_factor | warning |
| 4 | `missing_bars` | gaps in the expected trading-day sequence | any missing expected session | warning |
| 5 | `price_anomaly` | single-bar move beyond threshold | abs(close-to-close) > 20% | warning |
| 6 | `stale_data` | symbol not updated within expected frequency | no new bar within N expected sessions (default 5) | warning |
| 7 | `timezone` | **enforced, not flagged** — non-UTC-coercible timestamp | naive timestamp at ingestion | error (raises ValidationError) |
| 8 | `vendor_cross_validation` | conflicting prices for a symbol across adapters | rel. diff > 1% on overlapping bars | warning |

Check 7 is enforced at the PriceBar boundary (§2), so by the time the engine runs, timestamps
are already UTC; the engine's role for tz is to confirm/record, not to coerce.

---

## 6. TimescaleDB storage (DDL)

Managed via Alembic migrations (`make migrate`). OHLCV is a hypertable.

```sql
-- price_bars: hypertable on timestamp_utc
CREATE TABLE price_bars (
    symbol        TEXT          NOT NULL,
    timestamp_utc TIMESTAMPTZ   NOT NULL,
    open          NUMERIC(18,6) NOT NULL,
    high          NUMERIC(18,6) NOT NULL,
    low           NUMERIC(18,6) NOT NULL,
    close         NUMERIC(18,6) NOT NULL,
    volume        BIGINT        NOT NULL,
    adj_factor    NUMERIC(10,6) NOT NULL,
    source        TEXT          NOT NULL,
    quality_flags JSONB,
    PRIMARY KEY (symbol, timestamp_utc, source)
);
SELECT create_hypertable('price_bars', 'timestamp_utc');
CREATE INDEX ix_price_bars_symbol_time ON price_bars (symbol, timestamp_utc DESC);

-- fundamentals: plain relational table
CREATE TABLE fundamentals (
    symbol      TEXT NOT NULL,
    report_date DATE NOT NULL,
    pe_ratio    NUMERIC, pb_ratio NUMERIC, ps_ratio NUMERIC, ev_ebitda NUMERIC,
    revenue     NUMERIC, net_income NUMERIC, market_cap NUMERIC,
    sector      TEXT, industry TEXT,
    source      TEXT NOT NULL,
    PRIMARY KEY (symbol, report_date, source)
);

-- data_quality_reports: one per ingested series; linked from ExperimentManifest
CREATE TABLE data_quality_reports (
    id         UUID PRIMARY KEY,
    symbol     TEXT        NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    passed     BOOLEAN     NOT NULL,
    issues     JSONB       NOT NULL
);
```

---

## 7. Mandatory query pattern

**Every** price query filters by `symbol` AND a `timestamp_utc` range. Omitting either causes
a full hypertable scan that times out on multi-year data (ADR-003). No exceptions.

```sql
SELECT timestamp_utc, open, high, low, close, volume, adj_factor
FROM price_bars
WHERE symbol = :symbol
  AND timestamp_utc >= :start_utc
  AND timestamp_utc <  :end_utc            -- half-open [start, end)
ORDER BY timestamp_utc;                     -- ASC for backtests
```

- Ranges are half-open `[start, end)` to compose without double-counting boundaries.
- Bind parameters always (no string interpolation — injection + plan-cache).
- For "latest bar", still bound the range (e.g. last 7 days) then `ORDER BY ... DESC LIMIT 1`.

# Data Contracts (Cold Memory)

Formal schemas, storage DDL, and query rules for the data layer. Self-contained: read this
when working on `backend/app/data/`. Behavioral rules live in CLAUDE.md; domain heuristics in
the `data-engineer` agent. This doc holds the schemas, SQL, and check definitions.

Authoritative decisions: ADR-003 (TimescaleDB), ADR-004 (canonical PriceBar, normalize at
ingestion), ADR-005 (DataSourceAdapter), ADR-006 (quality gate).

---

## 1. `source` enum

```
Source = Literal["yfinance", "polygon", "alpaca"]
```
yfinance is primary (no key). Polygon is added in Phase 3 (enables vendor cross-validation).
Alpaca (`app/data/sources/alpaca.py`, ADR-019) is a third adapter added for cloud reliability —
yfinance is flaky from GitHub-runner IPs; Alpaca's free tier is built for programmatic access.
Bars are requested pre-adjusted (`adjustment=all`); `close == adj_close` by construction.

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
| `source` | `Source` | `"yfinance" \| "polygon" \| "alpaca"` |
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
    id: UUID                       # stable before/during/after persistence; manifest lineage key
    symbol: str
    source: Source | None          # adapter checked; None = legacy/direct unknown provenance
    checked_at: datetime          # tz-aware UTC
    issues: list[DataQualityIssue]
    passed: bool                  # downstream MUST verify passed is True (ADR-006)
```
`passed` is `False` if any issue has severity `"error"`. `warning`/`info` do not fail the gate
but are recorded. The report creates its UUID before persistence; TimescaleDB stores that exact
value so `ExperimentManifest.data_quality_report_id` can identify the checked snapshot (ADR-136).
Wording is always "flags potential X" (CLAUDE.md rule 6).

Single-name StrategyLab acquisition runs the same engine before search and embeds the complete
passed report in each new `Experiment`; its `ExperimentManifest.data_quality_report_id` points to
that exact embedded evidence (ADR-137). This makes cloud-generated pool rows self-contained when no
TimescaleDB repository is present. Historical pool rows retain null lineage rather than receiving a
guessed report.

Cross-sectional production hunts apply the same boundary independently to every requested symbol
and persist the complete reports for exactly the columns that survive panel construction
(ADR-138). Their ordered panel manifest maps each retained symbol to its report UUID, source,
adapter version, and request range. A skipped or short-history name is not represented as evidence
for a panel claim it did not enter.

Single-name forward scoring, lifecycle decisions, and paper-order target sizing also consume only
`ResearchDataset` values (ADR-139). Each new persisted forward score carries a frozen
`ResearchDatasetEvidence`: the complete passed report, source, adapter version, requested half-open
range, and executed revision. The report symbol must equal the managed position symbol. Legacy
scores keep `None`; failed or mismatched evidence produces no new score or target.

Cross-sectional forward scoring requires an exact mapping of every frozen universe symbol to a
`ResearchDataset` (ADR-140). Reports must match their mapping symbols, every component must name one
executed revision, and panel alignment must retain the frozen columns in order. Any component
failure leaves the prior factor score unchanged; a new score stores ordered
`ResearchDatasetEvidence` for the complete panel.

Static fundamental factor inputs are part of the cross-sectional claim (ADR-142). New experiments
store value and quality mappings projected into retained panel order; `None` means that family was
not supplied. Forward promotion copies those exact snapshots, never the current fundamentals pool.
Legacy value/quality graduates without the required map remain readable but cannot be promoted.
ADR-143 makes those mappings defensive immutable copies, rejects non-finite values and keys outside
frozen universe order at both model boundaries, and explicitly serializes them back to the same JSON
object shape. Absent keys remain deliberate score missingness; `None` remains legacy/unsupplied.
ADR-144 makes a cross-sectional forward position's parameters and ordered universe defensive
immutable values as well, while preserving their JSON object/array representations. These fields
are reconstruction identity, not mutable lifecycle state.
ADR-145 deep-freezes the complete originating cross-sectional experiment graph, including its
ordered panel identity, trials, selected graduate, gate verdict, manifest components, reports,
issues, and issue context. The same JSON object/array schema remains durable, but already-validated
quality lineage cannot be mutated in place before a later store write or forward promotion.
ADR-147 deep-freezes the corresponding single-name experiment graph, including trial order and
parameters, selected graduate and gate verdict, fundamental screens, valuation flags, manifest,
quality issues, and nested context. Reload binds all evidence to one selected trial and symbol;
production valuation enrichment must re-enter validation rather than inject an unchecked model
copy. Legacy selected-index absence and the existing JSON schema remain unchanged.
ADR-148 applies that complete durable boundary to single-name paper positions. Parameters, exit
reasons, score curves, and embedded evidence are defensive immutable copies; lifecycle state,
evidence symbol, counts, finite statistics, and non-empty curve geometry are validated on
construction, managed replacement, reload, and store write. Empty legacy curves and absent legacy
evidence remain explicit supported states.
ADR-149 applies the same complete boundary to cross-sectional forward positions. Lifecycle reasons,
score curves, and ordered component evidence are defensive immutable copies. The boundary validates
open/retired identity, finite cost and score statistics, unique ordered universe membership, exact
evidence order plus one executed revision, and non-empty curve geometry on construction, managed
replacement, reload, and store write. Evidence-null and empty-curve compatibility remains explicit.
ADR-150 requires every persistent experiment-pool writer to revalidate incoming model dumps before
any filesystem mutation. This applies to monolithic and partitioned single-name pools and the
cross-sectional pool, preventing unchecked model copies from bypassing ADR-145/147 at write time.

ADR-155 hardens `data/fundamentals_pool.json`, the separate ADR-029 company-score record that feeds
cross-sectional factors. Each `FundamentalRecord` defensively freezes its flags, rejects non-finite
or out-of-range scores, constrains F-score to `[0, 9]`, and requires the combined score to equal the
quality/value product exactly when both legs exist. Merge revalidates existing and incoming rows
before deduplication; the durable JSON keeps flags as arrays and all prior field shapes unchanged.

---

## 5. The 8 quality checks (formal definitions)

Run by `DataQualityEngine` (`app/data/quality/`). All thresholds are configurable; defaults
shown. Checks FLAG potential issues — they do not guarantee correctness.

> **Build status:** implemented today = #1 survivorship (info), #2 split/dividend, #3
> corporate_action (ADR-113/114), #4 missing_bars, #5 price_anomaly, #6 stale_data (warnings),
> plus `insufficient_data`, `symbol_mismatch` (ADR-115), `duplicate_timestamp`, and
> `source_mismatch` (ADR-118) structural errors; #7 timezone is enforced at the PriceBar boundary.
> **NOT yet implemented:** #8 vendor_cross_validation (needs the Polygon adapter, Phase 3+).
> See ARCHITECTURE.md §0.6.

| # | Check id | What it flags | Default threshold | Severity |
|---|---|---|---|---|
| 1 | `survivorship_risk` | universe may exclude delisted symbols — **risk flag only, not solved** | n/a (always informational when universe is yfinance-sourced) | info |
| 2 | `split_dividend_consistency` | implausible `adj_factor` jump between consecutive bars | factor ratio outside [0.5, 2.0] step | warning |
| 3 | `corporate_action` | adjusted-price discontinuity suggesting delisting/merger/remap | adjusted-close gap > 50% (independent of adj_factor; ADR-114) | warning |
| 4 | `missing_bars` | gaps in the expected trading-day sequence | any missing expected session | warning |
| 5 | `price_anomaly` | single-bar move beyond threshold | abs(close-to-close) > 20% | warning |
| 6 | `stale_data` | symbol not updated within expected frequency | no new bar within N expected sessions (default 5) | warning |
| 7 | `timezone` | **enforced, not flagged** — non-UTC-coercible timestamp | naive timestamp at ingestion | error (raises ValidationError) |
| 8 | `vendor_cross_validation` | conflicting prices for a symbol across adapters | rel. diff > 1% on overlapping bars | warning |

Check 7 is enforced at the PriceBar boundary (§2), so by the time the engine runs, timestamps
are already UTC; the engine's role for tz is to confirm/record, not to coerce.

Before the time-series heuristics run, every non-empty list must contain exactly the normalized
symbol named by its `DataQualityReport` (ADR-115), exactly one bar per UTC timestamp, and exactly
one source matching the ingestion adapter (ADR-118). Mixed/mislabeled symbols, duplicate calendar
rows, or mixed/mislabeled sources emit structural errors and are not compared pairwise or stored by
the ingestion pipeline. Direct quality-engine callers that have no adapter identity may omit the
expected source, but a mixed-source list still fails. Pipeline reports persist the expected adapter
source even on a mismatch; direct checks derive source only from a non-empty homogeneous bar set.
Existing reports remain explicitly `None` rather than inferring history (ADR-135).

The ingestion pipeline also binds the adapter result to its requested half-open `[start, end)`
range (ADR-119). Any pre-start or end-inclusive/later timestamp emits `range_mismatch`, returns
before pairwise heuristics, and blocks the entire list from storage. Direct quality-engine callers
without an acquisition request may omit both expected bounds; supplying only one bound is invalid.
The request itself must contain two timezone-aware instants with `start < end` (ADR-132/133). The
pipeline enforces this before adapter access, and every public range-bearing API rejects the same
malformed interval before repository or adapter access; aware non-UTC offsets remain valid instants.

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
    source     TEXT,                    -- nullable only for legacy/direct unknown provenance
    checked_at TIMESTAMPTZ NOT NULL,
    passed     BOOLEAN     NOT NULL,
    issues     JSONB       NOT NULL
);
```

---

## 7. Mandatory query pattern

**Every** price query filters by `symbol`, `source`, AND a `timestamp_utc` range. Omitting the
symbol or range causes a full hypertable scan that times out on multi-year data (ADR-003).
Omitting source can combine multiple vendors at one timestamp or reuse the wrong adapter's cache
(ADR-134). No exceptions.

```sql
SELECT timestamp_utc, open, high, low, close, volume, adj_factor
FROM price_bars
WHERE symbol = :symbol
  AND source = :source
  AND timestamp_utc >= :start_utc
  AND timestamp_utc <  :end_utc            -- half-open [start, end)
ORDER BY timestamp_utc;                     -- ASC for backtests
```

- Ranges are half-open `[start, end)` to compose without double-counting boundaries.
- Source is the active adapter's exact canonical `Source`; ordinary reads never fall back across
  vendors. Explicit vendor cross-validation is a separate future operation.
- Ingestion verifies every returned bar belongs to the same half-open request before storage
  (ADR-119); repository filtering is not a substitute for adapter provenance validation.
- Bind parameters always (no string interpolation — injection + plan-cache).
- For "latest bar", still bound the range (e.g. last 7 days) then `ORDER BY ... DESC LIMIT 1`.

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
| `quality_flags` | `dict \| None` | `None` means clean. Defensive finite JSON with string keys; immutable in memory (ADR-157) |

**Decimal precision**: stored as `NUMERIC(18,6)` (price), `NUMERIC(10,6)` (adj_factor). Use
`Decimal`, never `float`, so values round-trip exactly.

**adj_factor invariant**: applied exactly once, at ingestion. Re-applying downstream yields
prices that are `adj_factor`× wrong — a bug, not a feature.

**Validation rules (enforced in the model)**:
1. `timestamp_utc` tz handling above (UTC coercion — ADR-006; this is enforced, not flagged).
2. all four prices finite and > 0 (§8 invariant #1).
3. OHLC ordering: `low <= open,close <= high` and `low <= high`.
4. `volume >= 0`; `adj_factor > 0`.

ADR-157 makes the complete canonical observation defensive. `quality_flags` mappings/sequences are
recursively copied and frozen and accept only JSON-compatible leaves, string object keys, and finite
floats. Both repository implementations reconstruct the complete incoming batch before retaining
state or opening a database transaction; invalid unchecked copies reject atomically. Existing JSON
objects, primary-key overwrite/upsert semantics, OHLC rules, and SQL schema are unchanged.

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
    issues: tuple[DataQualityIssue, ...] # immutable in memory; serialized as a JSON array
    passed: bool                  # downstream MUST verify passed is True (ADR-006)
```
`passed` is `False` if any issue has severity `"error"`. `warning`/`info` do not fail the gate
but are recorded. The report creates its UUID before persistence; TimescaleDB stores that exact
value so `ExperimentManifest.data_quality_report_id` can identify the checked snapshot (ADR-136).
Wording is always "flags potential X" (CLAUDE.md rule 6).

ADR-156 makes this complete claim defensive rather than only model-level frozen. Issue order is an
immutable tuple; every context mapping/sequence is recursively copied and frozen; and context accepts
only JSON-compatible leaves, string object keys, and finite floats. Both repository implementations
reconstruct incoming model dumps before retaining state or opening a database transaction. Existing
JSON arrays/objects, UUID/source lineage, checks, severities, wording, and thresholds are unchanged.

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

ADR-163 validates those lineage records at their own boundary: manifest timestamps are aware UTC,
revision/config/parameter hashes have their full hexadecimal identity, shared fields are non-empty,
symbols are normalized, and acquisition intervals are ordered. Panel component records are
reconstructed and exposed through an immutable ordered list while retaining the JSON array shape.
Complete experiment boundaries still relate each manifest to the selected trial and embedded report.

Single-name forward scoring, lifecycle decisions, and paper-order target sizing also consume only
`ResearchDataset` values (ADR-139). Each new persisted forward score carries a frozen
`ResearchDatasetEvidence`: the complete passed report, source, adapter version, requested half-open
range, and executed revision. The report symbol must equal the managed position symbol. Legacy
scores keep `None`; failed or mismatched evidence produces no new score or target.
ADR-251 applies the manager's existing normalized target-symbol comparison at
direct evaluate_forward entry, before frame access and zero/nonzero-forward
scoring. Another asset's dataset cannot produce a standalone score for the target;
matched native scores, evidence and caller state retain their existing semantics.

Cross-sectional forward scoring requires an exact mapping of every frozen universe symbol to a
`ResearchDataset` (ADR-140). Reports must match their mapping symbols, every component must name one
executed revision, and panel alignment must retain the frozen columns in order. Any component
failure leaves the prior factor score unchanged; a new score stores ordered
`ResearchDatasetEvidence` for the complete panel.
ADR-252 enforces the same exact ordered panel columns at direct score_forward
entry before calendar access and zero/nonzero-forward scoring. Matching synthetic
panels may still omit evidence; mismatched membership/order refuses rather than
silently transforming the frozen factor or its equal-weight benchmark.
ADR-253 also reconstructs any supplied score evidence through the existing leaf
boundary and binds normalized ordered report symbols to the frozen universe before
scoring. None, valid model leaves and raw dictionary leaves remain supported; native
source/revision checks and output arithmetic retain their existing rules.

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
ADR-375 adds admission_policy to that single-name claim graph. Outer null/absence
means unknown historical/direct-search rubric, never inferred off. A present frozen
object requires both nullable config keys; null legs mean inactive optional screens.
Complete active configs must reconstruct without changing canonical finite JSON,
including raw evidence types/default keys. Ordinary preconstructed configs retain
constructor coercions. Store revalidation preserves snapshots; old writers can drop
them when rewriting, and retention removes them with the row. No data migration or
new run-level archive is adopted. This records surviving-row rubrics only; source
availability/cutoff, requested roster and filtered/error outcomes remain unmeasured.
ADR-148 applies that complete durable boundary to single-name paper positions. Parameters, exit
reasons, score curves, and embedded evidence are defensive immutable copies; lifecycle state,
evidence symbol, counts, finite statistics, and non-empty curve geometry are validated on
construction, managed replacement, reload, and store write. Empty legacy curves and absent legacy
evidence remain explicit supported states.
ADR-249 re-enters complete Experiment validation at single-name freeze_graduate
before projecting a paper position. Unchecked source copies cannot lose their
invalid selected-trial, gate or business-veto evidence in the narrower projection.
Existing legacy selection/evidence absence and ADR-033's recorded failure cohort
remain supported; no paper criterion, threshold or generated record changes.
ADR-149 applies the same complete boundary to cross-sectional forward positions. Lifecycle reasons,
score curves, and ordered component evidence are defensive immutable copies. The boundary validates
open/retired identity, finite cost and score statistics, unique ordered universe membership, exact
evidence order plus one executed revision, and non-empty curve geometry on construction, managed
replacement, reload, and store write. Evidence-null and empty-curve compatibility remains explicit.
ADR-150 requires every persistent experiment-pool writer to revalidate incoming model dumps before
any filesystem mutation. This applies to monolithic and partitioned single-name pools and the
cross-sectional pool, preventing unchecked model copies from bypassing ADR-145/147 at write time.
ADR-250 re-enters complete CrossSectionalExperiment validation before forward
promotion projects its graduate and frozen inputs. Unchecked source copies cannot
discard invalid trial, gate or lineage relationships into a valid narrower position.
Existing absent lineage/holdout and None/partial/empty fundamental snapshots retain
their meanings; legacy required-snapshot refusals and all paper criteria remain.

ADR-155 hardens `data/fundamentals_pool.json`, the separate ADR-029 company-score record that feeds
cross-sectional factors. Each `FundamentalRecord` defensively freezes its flags, rejects non-finite
or out-of-range scores, constrains F-score to `[0, 9]`, and requires the combined score to equal the
quality/value product exactly when both legs exist. Merge revalidates existing and incoming rows
before deduplication; the durable JSON keeps flags as arrays and all prior field shapes unchanged.
ADR-373 separately requires finite numeric UndervaluationScore evidence at
validated construction/JSON and final producer return, preserving nullable
absence, finite values/coercions and existing flags/JSON shape. Nonfinite output
refuses rather than becoming unscored permission. Record-first hunt admission can
skip a symbol even with screening off, and a sweep shard may fail; prior provider
price acquisition can already occur. Unchecked copies, deep flag freezing,
score bounds and historical null recovery remain outside this correction (F316).
ADR-371 separately guards symbol projection: canonical CIK-keyed rows can share
a case-insensitive symbol label across companies. score_maps refuses multiple
distinct owners before missing-leg filtering; output keys keep original spelling.
The quality provider refuses only a requested ambiguous symbol, before frame
acquisition/search and without converting it to ordinary missingness. Existing
earlier value-provider ordering and same-CIK newest/tie behavior remain.
No source owner is inferred, pool row repaired or historical snapshot rewritten.

ADR-156 independently hardens the quality reports embedded by those research and forward claims.
Their issue/context graphs cannot drift under a stable report UUID, unsupported Python or non-finite
context leaves fail at validation, and memory/TimescaleDB writes revalidate unchecked copies.

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

## Finite fundamental-screen minima (ADR-377 / FINDING-319)

FundamentalCriteria requires finite non-null min_revenue_growth_yoy and
min_net_margin at ordinary validated construction and JSON loading. NaN could
otherwise admit finite negative evidence through an enabled check. None still
disables that check; default zero, all finite values/coercions and screen
comparisons/reasons remain. This constructor contract does not revalidate
unchecked copies or certify FundamentalSnapshot numeric evidence/provenance.
No parser, provider fallback, search, graduation threshold, v14 or generated
record changes; no actual affected hunt or false graduate is established.

## Enabled fundamental metric validity (ADR-378 / FINDING-320)

An enabled screen_fundamentals check returns an explicit failure for NaN or
infinite metric evidence after its existing None branch. Finite comparisons and
missing-value reasons stay; disabled checks still ignore their metrics. No new
exception can become provider-fallback absence, and negative infinity stays vetoed.
Snapshot construction/parser/JSON remain unchanged; nonfinite numeric evidence
can still serialize as null. That durable loss and invalid-versus-unavailable
provider policy remain open under F320. No source-truth/PIT, historical effect,
threshold, search, v14 or generated-record change is claimed.

## Canonical fundamental snapshot validity (ADR-379 / FINDING-320)

FundamentalSnapshot requires finite values in all six numeric fields at validated
construction/JSON and parser return. Nullable fields, defaults, finite coercions
and JSON shape stay. Existing Experiment/store reconstruction refuses invalid
nested copies; invalid persisted numeric snapshots refuse on load. Three hunt
wrappers rethrow ValidationError before their existing ValueError/OSError-to-None
fallback, including already-rejected malformed nonnumeric fields. The universe
records per-symbol errors before search. Plain parser/availability ValueErrors,
OSError, history/Annual models and custom-provider fallbacks retain old semantics.
ADR-378's enabled consumer guards remain as defense for unchecked numeric copies.
Historical values lost to null are unrecoverable; no source-truth, PIT, universal
invalid/unavailable distinction, threshold or v14 change is claimed.

## Derived gross-profit measurability (ADR-380 / FINDING-321)

Only the history parser's revenue-minus-COGS fallback requires a finite result,
otherwise raising OverflowError before AnnualFundamentals/scoring. Native finite
subtraction and direct GrossProfit precedence stay. History providers propagate
this arithmetic error; the universe handles it per symbol before search. The
fundamental sweep counts/skips acquisition-time OverflowError and continues, also
covering existing huge-integer conversion overflow; other arithmetic exceptions
retain their old behavior. Earlier pool rows may remain under existing retention.
No recovery, None/zero fallback, broad Annual/history/scorer policy, FCF change,
threshold, v14, generated-record or general financial-score correctness claim.

## Annual fact selection limits (FINDING-322)

The shared selector uses FY/form metadata and latest filed row per reported fy;
input order resolves equal-filed collisions. It does not verify duration or
observation-period agreement. Synthetic mixed-period rows can change revenue and
screen verdict solely by row order, or bind an older end date to a newer fy.
Initial evidence used accepted synthetic shapes. F322 session5 adds actual SEC
CompanyConcept rows: FY2018 metadata spans quarter/comparative periods, and the
isolated selector chooses a 91-day revenue row. Full CompanyFacts acquisition,
production tag precedence and downstream incidence remain unverified. The frozen
reader reconstruction is not raw HTTP evidence; see F322 for provenance and limits. Reporting
clarification changes no parser behavior. Runtime policy needs attributable frozen
vendor fixtures and a separate ADR/TDD, including instant balances, non-December
fiscal years and restatement ambiguity. ADR-116/117 adjacency is not period proof.

## Fiscal labels at valuation growth consumption (ADR-381 / FINDING-323)

The History/parser schema is unchanged. estimate_growth alone requires strictly
increasing fiscal_year labels for multi-row inputs, raising ValueError before
series selection. Empty/single-row growth stays None. Its CAGR denominator is
last label minus first label, not observation count minus one. This is conditional
label annualization and does not verify physical periods, PIT or missing years;
F322 stays open. DCF early base/shares returns can precede this consumption guard.
No generated data or historical inputs are reconstructed.

## ROA balance-period consumption limit (FINDING-324)

No History schema or parser change: the current quality scorer uses same-row
assets for ROA, whereas the cited paper uses beginning assets. Its ROA trend is
therefore a proxy; year-label adjacency does not certify balance-period identity.
Prior beginning assets need a third attributable balance observation. The
reporting-only clarification preserves runtime scores and generated records;
missingness, asset-domain, income-definition and F322 period policy need a
separate ADR/TDD before a correction. No real affected vendor row is established.

## Ordinary DCF configuration validity (ADR-382 / FINDING-325)

The DcfAssumptions model's four floating fields are finite on ordinary validated
construction and dictionary/JSON reload, including raw nested result inputs.
This preserves the nonnullable float JSON shape rather than serializing invalid
knobs to null. Existing instances/unchecked copies are separate; no new schema
field, coercion/range/count policy, default, arithmetic or provider fallback is
adopted. Complete disclosure and historical lost settings are not reconstructed.

## Finite numeric safety components (ADR-384 / FINDING-326)

SafetyScore requires finite non-null leverage_ratio/current_ratio at ordinary
construction and JSON validation, including financial_safety producer returns.
None, finite coercions, signed values and native formulas/clip thresholds stay.
Producer ValidationError propagates before quality clipping or distress comparison;
make_distress_provider keeps evaluation outside its acquisition fallback. A valid
insolvency veto plus invalid liquidity now refuses, never becomes unscored None.
A sweep scoring refusal may fail the shard before output; no skip/recovery policy
is added. Annual/history inputs, retained-earnings NaN-to-bool, nonfinite operands
producing finite ratios, unchecked instances and historical evidence stay outside
this numeric boundary. No threshold, accounting-v14 or generated-data change.

## Latest-year financial-safety input consumption (ADR-385 / FINDING-327)

financial_safety requires every present latest-year total_assets, total_equity,
total_current_assets, total_current_liabilities and retained_earnings value finite,
in that order, before arithmetic/comparisons and existing missing/zero shortcuts.
The first invalid field raises plain ValueError; None itself remains valid but
cannot hide another invalid operand. Consumer errors remain outside the distress
provider acquisition fallback; sweep scoring can fail before output. ADR-384
still refuses overflow from finite operands with ValidationError. Empty history,
finite native formulas/ranges/thresholds and global Annual/history schemas stay.
Older years, other fields/scorers, PIT/period claims and unchecked provenance are
outside this consumer guard; no historical evidence is recovered.

# Backtesting Spec (Cold Memory)

Formal contracts for the research engine (Phase 3). Read when working on
`backend/app/research/`. Decisions: ADR-007 (vectorized pandas/numpy, NOT vectorbt).
Behavioral rules live in CLAUDE.md; this holds shapes, formulas, and the oracle tests.

Current search accounting is v14 via ADR-289's certified PBO translation,
ADR-290's certified primary Sharpe translation and ADR-291's certified OOS
selection/test/control translation. Version numbers inside earlier
ADR summaries describe their adoption identity. F241 measures one new local fixed v14 iid-normal
cohort (200/200, zero errors/graduates/ADR018 survivors). F243 separately measures
a NEW fixed v14 Student-t5 stress (200/200, zero errors/graduates/ADR018 survivors),
without rerunning historical sources. Neither certifies power, bootstrap or real markets.
Historical v13/v12/v11 and frozen v10
cohorts retain executed attribution.
ADR-295 enforces original nonnegative nonboolean Integral prior counts at both
search entries and positive counts at MinBTL before shortcuts. Python-int
normalization precedes cumulative addition, avoiding NumPy scalar wrap. Valid
Python accounting/math and v14 fingerprints remain; historical counter schemas
and generated/frozen records are unchanged. See F249 for manual evidence and limits.


ADR-299 extends original count validity to persisted research claims: Trial and
its cross-sectional subtype require positive nonboolean Integral evaluated counts,
with omitted legacy default1 retained. Both experiment lifetimes are nonnegative
original Integral counts and cover the sum of recorded trial evaluations after
existing lineage validation. Accepted scalars normalize to Python int; larger
priors and empty-trial zero remain. Memory stores retain equal canonical snapshots
before append; JSON writers already revalidate. No field shape, aggregation,
retention, search math, threshold or v14 identity changes. All3318 committed
experiments were compatible in F253's fresh read-only audit; no hidden counts or
generated-file migration is inferred.


ADR-300 preserves represented per-symbol lifetime maxima during retention. Keep all
graduates and the newest N nongraduates, plus the first original maximum-count
nongraduate only when that maximum would otherwise disappear. At most N+1
nongraduates remain; quota0 still retains a positive prior. Records and the prior
policy's output order stay intact; witnesses append after their symbol's recent
rows. Both bounded interfaces require original nonnegative nonboolean Integral
quotas before iteration/path access. Migration still resolves None to the input
count for lossless movement. No discarded historical count is inferred, and
search formulas, max aggregation, thresholds and v14 identity remain (F254).


ADR-301 validates the complete original HoldoutScore at gate consumption after
report/count/duration validation: positive nonboolean Integral bars, finite original
nonboolean Real score/return/benchmark values, original total return > -1. Checks
apply even when benchmark comparison is disabled; valid disabled comparison still
stays disabled. Float inspection preserves native operands and local bar count
normalizes to Python int. Construction, math, thresholds, config hash, v14 and
persisted fields remain. This is scalar validity, not benchmark provenance or
proof that float projection replays exact-real predicates (OpenF256; F255).


ADR-302 requires unique ascending original whole indexes at both public holdout
splitters, after existing fraction validation and before length/slicing/size work.
Checking only each slice misses inverted sorted halves or duplicate dates across
the cut. Valid ordered generic/naive/aware indexes retain exact original slices
and size behavior; no sorting, deduplication, timezone/cadence or floor arithmetic
changes. Normal ResearchDataset already protects production chronology; direct
single-name search was independently vulnerable (F257). Cross-sectional full-panel
kernels already refuse the malformed source downstream. No score, threshold,
accounting-v14 or frozen/generated evidence changes.


ADR-303 binds daily discovery to one current-master revision prepared after its
workflow concurrency wait. All shards and consolidation consume the same full SHA
and current-attempt binding before checkout; stale failed-only reruns require all
jobs to rerun. Upload/download names isolate attempts while current-attempt partial
shard handling remains. Manual dispatch uses master science code/universe files,
independently of its event-selected workflow DAG. Experiments retain actual git
lineage; publication uses a runner-local branch and explicit HEAD:master. This
protects the committed prior used by search (F258), not missing historical counts
or synchronized vendor retrieval. Search math, thresholds and v14 remain.


ADR-304 gives both portions from both public holdout splitters independent deep
numeric buffers and explicitly copied axes. A readonly pandas column view can
otherwise expose the full writable source owner through public NumPy.base,
including held-out prices. research.frames.copy_frame reuses the exact ADR-165
copy recipe; dataset retains its private alias and descriptor semantics. Logical
values/dtypes/axes, geometry, guards and scoring formulas remain. Extra O(source)
allocation is intentional. This is numeric/axis separation, not recursive object
or attrs isolation, direct-constructor freezing or a hostile-code sandbox. No
actual catalog lookahead/cohort effect is established; measured standalone payload
matches cannot certify universal layout-independent bitwise math (F259).


ADR-305 validates original min_holdout_bars and min_search_bars as nonnegative
nonboolean Integral counts after fraction/calendar checks, normalizing accepted
scalars to Python int before arithmetic. Unsigned native subtraction could otherwise
wrap an impossible holdout into a full-source search and empty tail. The original
fraction/floor recipe and insufficient-search error remain; an additional guard
requires both actual portions nonempty before copy/slicing. Zero floors remain
valid when fractional geometry is nonempty. Default search callers already use
safe fixed floors; no production occurrence, false graduate or cohort effect is
established. Scores, defaults, thresholds, fingerprints and v14 remain (F260).


ADR-306 extends the shared frame snapshot's axis recipe to categorical definitions.
Pandas deep copying separates codes but can retain writable numeric category owners,
allowing search-side category writes to change source/holdout labels even while
prices remain isolated. CategoricalIndex reconstruction copies codes/categories;
MultiIndex copies recursively replace every level through public pandas APIs.
Original values, category/level order, names, ordered flags, NA codes and unused
metadata remain. Ordinary axis/numeric copying, dataset alias/descriptor, split
guards, scoring, thresholds and v14 stay. Bounded common-axis controls found only
the category alias; this is not universal extension/object isolation (F261).


---

## 1. Price frame convention

Strategies and the engine operate on a pandas DataFrame, not raw PriceBars:

- **Index**: tz-aware UTC `DatetimeIndex`, ascending, unique.
- **Columns**: at least `close` (float). May include `open`/`high`/`low`/`volume`.
- Built from `list[PriceBar]` via `bars_to_frame(bars)` (uses adjusted `close`, as `float`).

`float` is used inside the engine (vectorized numpy math); `Decimal` is the storage/contract
type (PriceBar). The conversion happens once at `bars_to_frame`.

ADR-157 hardens each canonical `PriceBar` before that conversion: optional `quality_flags` are
defensive finite-JSON copies, and both repositories revalidate an entire incoming batch before any
state or transaction access. Unchecked model copies therefore cannot inject invalid OHLC/identity
or partially overwrite cached evidence; frame construction and adjustment semantics are unchanged.

---

## 2. BaseStrategy contract

ADR-346 gives the shipped cross-sectional xs_52w_high factory a stable
module-owned identity with unchanged lazy coercion/mapping capture/signals.
ADR-347 installed attributed high-method readers before ADR-348's restricted
pandas3.0.6/Cython/native Float64/shipped-window producer support. Per-allocated-
config before/after runtime receipts must match and travel with the existing
matrix; later measurement uses that saved domain. Missing/inconsistent receipts
raise, while unreviewed versions/engines remain explicitly unsupported and retain
primary eligibility. No engine is forced or option mutated. The reviewed max
selects in-window operands; previous weights/current turnover give D=W. Existing
primary math, three shifted-family evidence and all scientific caveats remain.
See validation-methodology.md and ADR348 for exact domain, geometry and limits.

ADR-349 adds stable alpha9_factory identity with the exact prior lazy window
lookup/int coercion and mapping capture. Its distinct v3 reader contract prepares
lags4/6/11 for prospective W+1 source support, preserving row1 early -d trading.
Actual Alpha9 remains unsupported; signal, portfolio and producer ASTs stay.
Reader metadata is not proof that a named runtime executed.

ADR-350 subsequently adopts restricted Alpha9 producer support with exact
pandas3.0.6/Cython and matching per-config generation-time receipts. Historical
HighRuntime names carry each family's independent version/engine observations;
classification never uses later globals. Native Float64/shipped-window support
uses max(actual W+1), v3 and actual kept-fold pairing; high stays W/v2. Missing
receipts raise; unaudited/custom domains stay unsupported. No engine, early -d,
signal/portfolio formula, primary selector, threshold or v14 changes. See ADR350
and validation-methodology.md for numerical-history/PIT/calibration limits.

ADR-351 gives Alpha4 a stable module-owned factory with the exact prior lazy
window lookup/int expression, mapping capture, errors and5/9/21 grid. Its
rolling.apply percentile callback counts <= ties fully and keeps W-1 NaN warmup;
neither that callback nor execution arithmetic changes. Alpha4 PCV remains
unsupported. This identity prerequisite adopts no runtime/source support or
new readers; a future scientific decision must audit actual callback/NumPy/
rolling-admission dependencies rather than pandas Rolling.rank.

ADR-352 subsequently prepares distinct pandas3.0.6/Cython/NumPy2.5.4 Alpha4-v4
readers and rolling-alpha4-percentile-v1. Supported/no-fold lags5/9/21 and full
window/allocated-coverage binding preserve mixed existing methods and structural
checks. Actual Alpha4 stays unsupported; no callback, producer or runtime-capture
change. Future strict measurement needs a separate NumPy/pandas/engine saved-domain
decision. Reader attribution cannot certify actual execution or source provenance.

ADR-353 subsequently enables restricted Alpha4 measurement using a dedicated
frozen Alpha4Runtime with saved generation-time pandas3.0.6/NumPy2.5.4/Cython
identity. Exact known factories require matching before/after and cross-config
receipts; HighRuntime/high/Alpha9 stay unchanged and later globals cannot relabel
matrices. Missing/wrong receipts raise; unknown pandas, NumPy and engine domains
remain unsupported v1 in that order, with unsupported_numpy_version added to
backend/API/client reason readers and display. Native Float64/shipped windows
use D=max(actual W), E=max(floor,D), distinct v4 and actual kept-fold pairing.
The <= percentile callback, ties, W-1 warmup, primary arithmetic and thresholds
remain exact; no engine option is forced. The support caption includes Alpha4
without inventing historical fold attribution. Runtime metadata is bounded
attribution, not build/provenance/PIT/independence or calibration attestation.
Other unsupported recipes and FINDING-272 remain; v14/generated/frozen evidence
and all noncausal selection/switching-account limitations stay unchanged.

ADR-354 gives xs_decay_reversal a stable module-owned factory while preserving
its exact lazy inner lambda, mapping reference, int coercion/errors, call-time
signal lookup and3/5/10 grid. Signals and first W NaN warmup stay unchanged.
Actual decay PCV remains unsupported; no capture/reader/source support is adopted.
Future scientific review must follow pct_change/rolling.apply/np.dot, finite
return admission, BLAS dispatch/build domain and operative W+1 endpoints rather
than borrowing Alpha4's percentile proof. Existing F265/F272 limitations remain.

ADR-355 prepares separate decay-reversal v5 readers identifying pandas3.0.6
Cython/NumPy2.5.4 decay-weighted returns with rolling-decay-reversal-v1 and
supported/no-fold lags4/6/11. Full trials bind window3/5/10 and covering
maxlag>=window+1; compact views retain structural checks without finalist or
execution replay. Mixed v1-v5 preserve complete common requests, scalar/geometry
and attributed WF-bar agreement. Fold details qualify the stored recipe, while
the actual support caption stays unchanged. Actual decay remains unsupported;
no callback, capture, support resolver, measurement or evaluator changes.
Prospective source/endpoint evidence does not adopt saved runtime policy or
certify build/provenance, independence, PIT, switching-account performance or
panel calibration. A separate producer ADR/TDD remains necessary. Existing
F265/F272 limits, thresholds, fingerprints, v14 and generated/frozen records stay.

`app/research/strategies/base.py`. ABC:

- `generate_signals(data: pd.DataFrame) -> pd.Series`
  - returns a float position weight per bar, **in [-1.0, 1.0]** (−1 short … 0 flat … +1 long).
  - index MUST equal `data.index`.
  - **No look-ahead**: signal at time *t* may use only data up to and including *t*.
- `research_citations: list[str]` — non-empty; cite the real paper.
- `name: str`, `parameters: dict` (for the manifest's parameter hash).

### Strategy catalog (ADR-010)
The authoritative list of strategies lives in `app/research/strategies/catalog.py` and is
served to the frontend via `GET /api/v1/strategies`. **Don't maintain a copy here** — the
list drifts. The catalog carries each strategy's UI label, description, citations, and
parameter schema; the frontend renders the form generically from it.

Adding a strategy is a 5-line backend-only change (subclass + Pydantic config + dispatch +
catalog entry + consistency-test map). See ADR-010 "Pattern for adding a strategy". The
consistency test (`tests/unit/test_strategy_catalog_consistency.py`) is load-bearing: it
guarantees catalog ↔ Pydantic field-name parity and that every catalog default round-trips
through API validation.

---

## 3. BacktestEngine (vectorized, ADR-007)

**Why hand-rolled, not a library (2026 landscape — don't relitigate without new info):**
The engine is intentionally a ~50-line pure pandas/numpy kernel, guarded by the §8 oracle tests.
The library options were researched and rejected for *this* project:
- **vectorbt (OSS)** — fails to build on Python 3.12 (numba → llvmlite native build); OSS is
  effectively frozen behind the paid **vectorbt PRO** (closed-source, $20/mo) — unusable in a
  public portfolio repo a reviewer must clone and run.
- **backtrader** — active development stopped ~2018; 3.10+ friction; event-driven realism we
  explicitly don't need (ADR-001).
- **zipline-reloaded** — heavy, data-bundle ceremony, US-equity/factor oriented; overkill.
- **backtesting.py** — maintained + lightweight but **single-asset**; doesn't fit the
  `(T × N)` multi-config returns matrix that PBO/CSCV needs. (Possible *dev-only cross-check*, not the core.)
- **NautilusTrader** — execution-realism/live-parity focus; out of scope (ADR-001).
There is no maintained, free, OSS, 3.12-friendly *vectorized-sweep* library that fits — and
hand-rolling the correct math (look-ahead avoided, cost-on-turnover) is on-thesis for a project
whose whole signal is methodological rigor. Revisit only if sweeps hit 10^5–10^6 combos
(numpy-broadcast first; vectorbt PRO as a private research-only tool, never in the public repo).

`app/research/backtesting/engine.py`. Pure pandas/numpy. Given `prices` (close series) and
`signals` (position weights), `initial_capital`, and `cost_rate` (fraction per unit turnover):

```
returns      = prices.pct_change().fillna(0)
position     = signals.reindex(prices.index).clip(-1, 1).fillna(0)
# trade on the NEXT bar -> no look-ahead: yesterday's position earns today's return
gross        = position.shift(1).fillna(0) * returns
turnover     = position.diff().abs().fillna(position.abs())   # |Δposition| each bar
costs        = turnover * cost_rate
net          = gross - costs
equity_curve = (1 + net).cumprod() * initial_capital
```

`BacktestResult` (frozen): `equity_curve` (Series), `returns` (net Series), `metrics`
(`BacktestMetrics`), `n_trades` (count of nonzero turnover bars), `cost_rate`, `position`
(the clipped/filled position Series — exposed so API callers, e.g. `/backtest`'s
`trade_markers`, can derive signal-change events without re-running the strategy).

ADR-176 requires a unique ascending price index before returns or signal alignment. A positional
lag on an unordered calendar can use a later signal for an earlier return. Invalid calendars raise
rather than being sorted/deduplicated; ordered generic/naive indexes and sparse signal reindex/
clip/fill behavior remain supported. This does not certify actual daily cadence or strategy causality.

ADR-177 requires finite positive initial capital and finite nonnegative cost, then rejects any
nonfinite/nonpositive capital-scaled equity observation before publishing a result. A finite
return metric alone cannot establish representable scaled wealth. No capital/cost cap or wealth
floor is added; ordinary math, empty histories and extreme representable flat curves are retained.
Observed broker insolvency remains a separate account-ledger contract under ADR-169.

ADR-178 requires every supplied price to be real nonboolean numeric, finite and strictly positive
before pct_change. Missing first/interior/last observations and invalid singleton values raise
even for zero exposure, rather than becoming zero returns. Object/string/complex payloads are not
coerced; complete nullable numeric and empty numeric Series retain their existing semantics.
No observation is filled, dropped or repaired, and lag/cost/metric calculations are unchanged.

ADR-343 refuses exact signed infinity in the already reindexed signal Series
before the existing clip/fill path. Infinity cannot become full directional
exposure and finite reported performance (FINDING-293). NaN/pd.NA warmup, sparse
alignment, finite saturation and native finite wider values retain their native
arithmetic. Unmatched infinity remains discarded, including for empty prices;
aligned final/singleton infinity refuses even with zero cost. Existing price
error precedence stays. This is not full original-signal validation or causality
certification. Flagged unsupported Decimal/complex infinities already failed but
now refuse earlier; no universal exception/warning equivalence is claimed.
If encountered by search/calibration, the narrower completion domain can change
errors or denominators; no unchanged-rate claim follows. Finite estimators,
thresholds and accounting v14 remain; edited source provenance changes.

ADR-254 applies the same original-price dtype/domain boundary to populated
cross-sectional panels at asset_returns before pct_change. Native per-column
checks preserve nullable and wider numeric precision without float64 conversion.
Zero-cell panels and valid singleton first-period zero remain supported; missing,
nonfinite, nonpositive and nonreal prices cannot become finite portfolio evidence.
Original return/ranking/lag/cost arithmetic and source calendars remain unchanged.
ADR-255 requires the original cross-sectional price index to be unique and
ascending at asset_returns before price validation or pct_change. Invalid raw
calendars cannot publish a positional return using a future-dated source row.
No sorting/deduplication or UTC/cadence policy is added; ordered generic, naive,
aware, empty and singleton calendars retain their native results.
ADR-256 also requires populated native cross-sectional asset-return results to
be finite before portfolio multiplication/aggregation, so zero exposure cannot
hide overflow as a flat return. Original pct_change/fillna arithmetic, finite
extremes, nullable/wide precision and zero-cell panels remain; native arithmetic
overflow raises ValueError without changing NumPy error state or using a fallback.
ADR-257 qualifies cross-sectional tie handling: rank(method="first") follows
supplied column order, so fixed-order input is deterministic while permuting tied
symbols may change the chosen legs. The frozen ordered universe preserves this
reconstruction identity. No tie algorithm, return, cost or existing claim changes;
a different tie policy needs a separate methodology decision and validation evidence.

ADR-258 requires finite native cross-sectional cost evidence and final net returns.
Original negative comparison, operand, lag/turnover/net formulas and output dtype
remain; bool/Fraction costs, wide finite empty outputs and huge finite flat outputs
retain native accounting. Nonfinite derived net or native arithmetic overflow
raises ValueError without caps, float narrowing or NumPy error-state changes.

ADR-259 requires every supplied cross-sectional signal column to have a price
column before ranking. An unpriced ranked name cannot disappear during weight
projection and remove a neutral leg. Subset/reordered signals, sparse dates and
NaN warmup retain their original ranks/projection/lag/cost arithmetic; extra names
raise even for empty/flat histories. This adds no complete-panel or tie policy.

ADR-260 refuses exact signed infinity at the shared cross-sectional ranker before
ranking, after quantile validation. Overflowed momentum/reversal ratios cannot
become false supplied-order ties. Original NaN/pd.NA exclusion, finite native wide,
nullable/object numeric/bool compatibility and empty behavior remain. No dtype
ban, score conversion, estimator recovery or finite-precision certification is added.

ADR-261 preserves native wide floating score order by selecting an object-typed
rank input only when a native floating column is wider than float64. Pandas keeps
the native scalars instead of fabricating ties through narrowing. True ties retain
supplied order; original missing counts/weights/lag/costs and ordinary rank paths
remain. Longitudinal calibration identity is unchanged. This does not recover
already-rounded generator scores or certify arbitrary mixed integer/float precision.

ADR-262 also preserves represented score order for all-native numeric panels
mixing integer/float or signed/unsigned integer dtypes. Scalar-preserving object
rank avoids common-array floating promotion; exact represented integer/float
comparisons retain true supplied-order ties. Homogeneous, nullable and object
paths remain; small mixed dtypes share the object cost without value thresholds.
Original guards/counts/financial formulas and longitudinal calibration identity
stay. Already-rounded source values and unsupported mixed payloads remain outside
this correction; this does not certify universal arithmetic precision.

ADR-263 requires unique original cross-sectional price column labels at
asset_returns after calendar checks and before price validation/arithmetic.
Duplicate symbols cannot copy one ranked weight into multiple priced columns
and break neutrality. Duplicate zero-row axes also refuse; unique arbitrary
labels/order/native dtypes and valid zero-cell panels remain. No normalization,
deduplication or earlier portfolio guard is added. Original financial formulas,
error precedence and longitudinal calibration identity stay unchanged.

ADR-264 preserves native rank-IC inputs before pairwise masking on both signal
and forward-return sides. Native integer/wide frames use scalar-preserving
object inputs before where/rank; ordinary paths retain their original operation.
IC keeps average ties, paired NaN warmup/undefined-date dropping and original
correlation/summary formulas. Finite direct native IC values change where prior
narrowing fabricated ties; canonical float64 outputs and longitudinal calibration
identity remain. Infinity and summary-domain policies are separate limitations.

ADR-265 refuses exact signed infinity in original rank-IC signals after ordered
column matching and checked-price preparation, before pairwise masking/ranking.
Even final/unscorable infinities refuse; NaN/pd.NA warmup, native finite scores,
average ranks and all IC/summary arithmetic remain. No dtype ban, range cap or
summary-domain policy is added. Portfolio-first search already refuses these
inputs; longitudinal calibration identity and historical records are unchanged.

ADR-266 requires finite defined rank-IC outputs before projecting derived
endpoint roundoff to the proven [-1,1] correlation range. summarize_ic validates
each original scalar as finite real evidence within that range before conversion
or short-sample None. Native Fraction/Decimal/wide endpoint neighbors cannot
round into acceptance; raw observations are never clipped/filled/dropped.
Valid bool/numeric/empty/singleton behavior and all summary formulas/std floor
remain. Complex and numeric-string coefficient encodings refuse; no whole-dtype
or model-leaf rule is added. Derived endpoints may change an ULP, including
production; longitudinal calibration identity and historical records remain.

ADR-267 validates durable ICSummary leaves: finite scalars, std>=0, hit_rate in [0,1],
native integer periods>=2 excluding bool, always instance revalidation, and exact original
IR/t formula coherence with the unchanged std floor. Existing nested/store reconstruction
rejects bad claims before writes. Finite-only mean preserves coherent historical endpoint
roundoff; impossible-but-coherent finite metadata remains an explicit limitation. No
statistic repair, generated record rewrite, schema-field, selector or gate change.

ADR-314 validates cross-sectional shift-producing counts before panel access:
momentum lookback/skip, reversal lookback, residual momentum skip and Alpha19
change_lag must be original nonnegative nonboolean Integral scalars at the direct
function boundary. Python-int normalization precedes momentum period addition;
zero shifts remain causal and valid. Registry factories retain their existing int
coercion, so original factory scalar type/identity is not certified. Other rolling
parameters retain pandas policy. Shipped grids, signal formulas, ranking, lag,
costs, scoring, thresholds and longitudinal v14 identity remain unchanged.
This closes malformed negative-window lookahead in forward reconstruction;
arbitrary custom signal causality and point-in-time fundamentals remain separate.

ADR-315 adds a scored-wealth domain at cross-sectional _score_holdout: after
selecting the scored return slice, refuse any native return<=-1 before benchmark
preparation, product or Sharpe. An even number of negative gross factors cannot
certify positive-wealth performance. Raw portfolio_returns still reports finite
leveraged losses faithfully, and only unsafe periods inside the scored slice
trigger this guard. Valid native formulas, warmup, empty slices, thresholds and
longitudinal v14 remain; no liquidation, full-prefix account guarantee or new
compounding/projection recovery is introduced (FINDING-266).

**Invariants** (Hypothesis): equity_curve all finite & > 0 for finite inputs; zero signal →
flat equity, zero trades; higher cost_rate → total return monotonically ≤.

---

## 4. Metrics

`app/research/backtesting/metrics.py` — `BacktestMetrics` (frozen):

ADR-357 validates raw max_drawdown equity before its empty shortcut: original
real numeric nonboolean/noncomplex dtype and complete native finite observations.
Missing rows cannot disappear through pandas reduction; complex wealth cannot
lose its imaginary part at float conversion (FINDING-297). Native inspection
preserves finite wider inputs; no float64 source conversion or data repair is
introduced. Numeric empty zero, original operands, cummax/division/reduction and
clamp stay. This is source validity only: finite zero/negative equity and native
derived NaN, warnings or exceptions remain separate, including unsupported sparse
cummax. No universal finite-output claim, positivity floor, estimator, threshold,
policy hash, v14 identity or generated/frozen evidence change follows.

The standalone `return_moments` helper validates complete finite real nonboolean numeric input
before degenerate shortcuts (ADR-182). Missing rows cannot inflate PSR counts while pandas skips
them for skew/kurtosis. Finite short/constant or undefined higher-moment arithmetic remains None;
complete nullable numeric and finite signed samples retain native raw-kurtosis calculations.

ADR-183 applies the same complete-sample validation to the standalone Sharpe interval after
confidence validation and before length shortcuts. Missing padding cannot cross its one-year
minimum or narrow its band. The iid-normal estimator and valid short/constant behavior remain
unchanged. ADR-185 resolves FINDING-117 by applying the same source validation to standalone
Sharpe before its shortcuts, preserving valid signed/nullable and numeric degenerate conventions.
ADR-184 resolves FINDING-118 by evaluating the equivalent Gaussian quantile with
norm.isf((1-confidence)/2), preserving a representable near-one tail and finite interval bounds.
ADR-337 / FINDING-285 addresses the separately deferred central-quantile cancellation:
confidence<=0.5 uses sqrt(2)*erfinv(confidence), while the exact existing inverse-survival
expression remains above 0.5, preserving default 95% and high-tail arithmetic. The branch chooses
a numerical representation of the same Gaussian quantile, not a statistical threshold.
The central product uses Python floats, avoiding new NumPy scalar-multiply underflow
warnings/strict-policy failures without changing its binary64 quantile or error-state policy.
Complete zero-centered 252-row returns at confidence 1e-20 now retain representable nonzero
bounds. Forward Gaussian mass is a numerical quantile oracle, not empirical interval coverage.
Subnormal probability quantization and nonzero-center endpoint widths below float spacing remain
limitations; no uniform relative accuracy, correct rounding or dependence-robust coverage follows.
Source validation, history minimum, Sharpe/Lo-SE formulas, iid_normal metadata and API/UI shape stay.

ADR-203 gives exact constant Sharpe samples zero and exact constant higher moments None
before native arithmetic. Nonconstant native Sharpe must have finite mean/positive dispersion
and finite annualized score. Preserve measurable native answers; otherwise recover
the same sample score on maxabs-normalized returns, or raise ValueError if still
unmeasurable, consistently under strict NumPy state. Financial cost/sign property
domains remain intact; Decimal oracles verify tiny/huge/subnormal recovery.
Original pandas estimator/order, signed/nullable source domains and iid-normal interval math
remain. Finite primary score/moment corrections advance accounting identity to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-v8`; historical calibration is not
current evidence. Replacement distributions remain unmeasured; no dispatch/data edits.

ADR-204 detects native higher-moment underflow and returns None consistently across
ambient error modes, instead of finite fabricated kurtosis or FloatingPointError.
Original source validation and short/exact-constant precedence remain outside the catch;
native estimators/count remain. Former finite PSR inputs become unmeasured, so identity
advances to `whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-v9`.
ADR-205 resolves FINDING-145's separate Sortino arithmetic/representation question.

ADR-209 detects foundation Sharpe native mean/std/ratio underflow and certifies a
native zero mean with math.fsum of original float64 observations. Failed native
arithmetic or lost zero evidence invokes float64 maxabs-normalized sample std and
stable normalized sum, annualized and divided by std before dividing by n. This
preserves representable subnormal scores whose unannualized mean rounds to zero.
Nonzero native measurable scores retain their original
order; genuine cancellation and truly tiny scores rounding to zero remain. This
is a particular measurability correction, not a universal precision guarantee.
Accounting identity advances to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-v10`;
historical v9 measurements do not certify this procedure. All thresholds remain.

ADR-286 / FINDING-235 recovers original native/classic Float64 STD underflow or
finite collapse by anchoring differences before normalization, preserving original
fsum evidence and restoring the combined exponent once. Ordinary native results,
nonfinite STD, mean/ratio-only failures and other dtype families retain prior paths.
Subnormal control cases permit one output ULP; universal correct rounding is not
claimed. Accounting advances to verified-zero-anchored-dispersion-v11. Historical
v10 evidence remains attributed to its executed revision; v11 calibration is
unmeasured. Frozen cohorts, thresholds and generated records are unchanged.

ADR-290 / FINDING-239 also corrects native-accepted original Float64 Sharpe
dispersion when strictly same-sign nonzero values satisfy maxabs<=2*minabs.
That inclusive range certifies exact first-value subtraction; normalized-difference
sample STD avoids rounded source-level centering. Preserve the actual accepted
native mean and use separated mantissas with one exponent restoration. Original
STD/mean/ratio failures, zero means, mixed-sign/zero/wider-spread observations and
other dtype families retain prior paths. Primary Sharpe and its derived iid
confidence interval change; the interval formula/assumptions and other metrics
stay. Known-native-mean Fraction variance checks do not certify arbitrary native
numerator accuracy or universal correct rounding. Accounting advances to v13,
current calibration remains unmeasured and prior/frozen cohorts stay attributed.

ADR-208 gives annualized volatility native-first sample-std recovery. Source
validation precedes short/exact-constant zero. Preserve native positive finite
std * sqrt(252) when no underflow is detected; otherwise compute float64 maxabs-
normalized sample std, annualize, then restore scale. This retains representable
subnormal risk that native variance lost; recovered output must be positive finite
or raises ValueError. Exact constants no longer fabricate positive volatility.
Numeric API shape and descriptive-only identity stay; no universal precision proof.

ADR-287 / FINDING-236 anchors represented differences before normalization for
original native/classic Float64 STD underflow or finite collapse. Difference-scale
and normalized sample-STD mantissas are annualized before one combined exponent
restoration, retaining positive subnormal risk. Final rounded zero still refuses
under ADR-208. Ordinary native results, nonfinite STD, annualization-only failures
and other source families keep prior behavior. Subnormal controls permit one
output ULP; universal correct rounding is not claimed. This field remains
descriptive: accounting stays v11, calibration remains unmeasured, and frozen
historical cohorts and generated records retain their original attribution.

ADR-186 validates original complete finite real numeric source evidence at the public
compounded-return helpers before conversion/empty shortcuts; boolean, strings and complex
observations cannot be reinterpreted as measured returns. Numeric empty and log math remain.
ADR-211 locally ignores only log1p underflow after finite/>-1 checks, preserving
valid subnormal logs across platform-specific strict-state signals. Original
native logarithms, caller state and finite-positive wealth checks remain.

ADR-187 validates Sortino's finite real nonboolean target before complete numeric source evidence
and degenerate shortcuts; native full-sample downside arithmetic and finite signed domain remain.

ADR-205 keeps native measurable Sortino scores, then normalizes returns/target together
and negative shortfalls separately to recover overflow/underflow without changing the
full-sample denominator. Sortino is required nullable in BacktestMetrics and the API:
None means arithmetic remains unmeasurable, rendered "Not measurable"; measured short/
no-downside zero remains 0.00. The original engine financial property domains remain;
within the bounded test domain an absent ratio requires independent Decimal overflow
justification. Descriptive only, so ADR-205 did not itself change accounting identity.
General finite-result
precision remains a separate limitation. ADR-206 resolves target-related cancellation
(FINDING-146) by averaging original float64 per-observation excess for nonzero
targets, retaining exact pandas native mean at target zero. Float64 comparison
prevents narrow source dtype from rounding away shortfall (FINDING-147). Failed
native arithmetic normalizes finite excess first; only overflowing subtraction
normalizes source/target together. fsum stabilizes its fallback numerator.
ADR-210 resolves F152's recovery mean-first subnormal rounding by evaluating a
stable normalized sum with frexp-separated numerator/downside exponents and one
final ldexp. True overflow remains None; genuine tiny zero remains zero. Native
measurable results and calibration v10 stay. Loss during prior common-scale
normalization remains an explicit limitation.
ADR-212 corrects the new subnormal test oracle with exact Fraction squared-score
midpoint comparisons. Decimal sequential roots do not certify exact halfway
rounding. Full new property domains remain; normal relative checks and exact
3/100 fixtures stay. Subnormal error is measured in output units (one ULP in the
bounded audit), with nonzero/sign assertions retained; this is an explicit
precision limit, not a correctly-rounded production or changed gate claim.
ADR-207 resolves native mean/partial moment underflow (FINDING-148) and lost
native-zero residuals (FINDING-149): native underflow raises locally into scaled
recovery; native zero mean requires original float64 excess fsum zero. True
cancellation and legitimately rounded tiny ratios remain measured zero. Nonzero
native measurable scores remain; no blanket finite-precision guarantee applies.
Required nullable contract and descriptive-only calibration identity remain.

ADR-288 / FINDING-237 preserves original fsum evidence only for original
native/classic Float64 with default target zero and finite native downside RMS
underflow/collapse. Original negative shortfalls are normalized separately;
sum/downside mantissas restore one exponent difference after full-sample division
and annualization. Genuine cancellation, subnormal/signed-zero rounding and final
overflow None retain their meaning. Uncertifiable fsum overflow, nonfinite RMS,
mean/ratio-only failure, nonzero targets, other families and ordinary native
results keep prior paths. Selected exact oracles and ADR-212's one-output-ULP
subnormal controls do not certify universal precision. Descriptive accounting
stays v11, current calibration is unmeasured and frozen cohorts remain unchanged.

ADR-188 validates both Calmar scalar inputs before zero-drawdown shortcuts and rejects a
nonfinite native quotient; finite signed ratio semantics and the absolute denominator remain.

- `sharpe`: `sqrt(252) * mean(net) / std(net)` (daily). 0.0 if std==0 (constant returns).
- `max_drawdown`: `min(equity/equity.cummax() - 1)` — **in [-1.0, 0.0]**. Positive = bug.
- `total_return` (ADR-110): `product(1 + net) - 1` over every net observation, including the
  first bar's initial-position cost. It is never derived from `equity[-1]/equity[0]`, because the
  first equity observation is already post-return and would drop that first period.
- `annualized_return` (ADR-110): the geometric compound rate
  `product(1 + net) ** (252 / n) - 1`; it therefore always has the same sign as total return.
  Non-finite returns or a non-positive compounded-wealth path fail closed instead of emitting a
  misleading scalar. `annualized_vol` retains standard sqrt(252) scaling.
- `sortino` (ADR-107): `sqrt(252) * mean(net) / downside_semi_std(net)` — same sqrt(252)
  convention as Sharpe, but the denominator only squares shortfall below target 0.0 (upside
  dispersion never penalizes) and divides by the full sample size. 0.0 if no return falls below
  target, mirroring Sharpe's degenerate-series convention rather than +inf. **Descriptive only —
  not read by the gate, PBO, DSR, or any threshold** (charter §4).
- `calmar` (ADR-108, corrected by ADR-110): geometric `annualized_return / abs(max_drawdown)` — a pure ratio of two other
  `BacktestMetrics` fields, not a new estimate from the returns Series. 0.0 if `max_drawdown ==
  0.0`, same degenerate-series convention. **Descriptive only**, same as `sortino` above.
- `sharpe_ci` (ADRs 109, 111): `SharpeConfidenceInterval | None` — a 95%-default iid-normal confidence interval on
  `sharpe` via Lo (2002)'s asymptotic standard error, `sqrt((1 + SR^2/504) / years)` where `years =
  len(returns) / 252`. A DIFFERENT question than PBO/DSR (selection bias across a search): this is
  the sampling uncertainty in one already-observed Sharpe. `None` below 2 returns or below 1 year
  of data (the asymptotic normal approximation is unreliable there) — callers must handle null.
  Re-derives the same formula `app/research/lab/frontier.py`'s `sharpe_standard_error` (ADR-043)
  uses rather than importing it: `backtesting/` sits below `lab/` in this codebase's layering.
  The interval carries `assumption: "iid_normal"`; serial correlation or non-normal returns can
  make it too narrow. `confidence` must be finite and strictly between 0 and 1. **Descriptive
  only.** Rendered in `BacktestResultView` as an `IID-normal 95% interval: lower – upper` line
  under the Sharpe tile when present, nothing when `null`.

---

## 5. BenchmarkComparator

`app/research/benchmarks/comparator.py`. Default benchmark SPY. Given strategy `net` returns
and `benchmark` returns (aligned), requires at least two finite overlapping observations and each
return greater than -1 (ADR-112):

ADR-172 also requires each source index to be unique and ascending before inner alignment. It
preserves valid partial overlap and generic/naive ordered indexes; malformed calendars raise rather
than being sorted or deduplicated. Calendar identity is intrinsic and does not certify acquisition.

ADR-179 requires both source Series to have real nonboolean numeric dtype before alignment.
Object/string/complex/boolean payloads raise rather than being coerced or partly discarded.
Complete nullable numeric inputs remain supported; missing overlapping rows fail the finite check.
Finite/value validation still concerns aligned rows only, preserving partial-overlap semantics.

ADR-180 requires every published comparator scalar to be finite. Upper arithmetic failures
become ValueError rather than NaN/infinite claims, preserving the API's optional comparison.
Estimator formulas remain unchanged; extreme representable answers may be declined when their
intermediates overflow. Finite outputs alone do not certify arithmetic precision.

ADR-181 recovers beta with a scaled sample covariance ratio only when native benchmark variance
is zero despite distinct observations. Identical tiny nonconstant returns therefore retain beta
one; all-zero strategy and true constant benchmark retain beta zero. Native positive-variance
arithmetic and other statistics remain unchanged. FINDING-113 distinguishes this repaired case
from positive subnormal variance/covariance underflow and other tiny-moment limitations.

ADR-268 extends that recovery trigger to underflow signaled during native benchmark variance,
covariance or the beta quotient. Ordinary native beta and existing constant conventions remain;
the same separately normalized covariance ratio recovers affected positive-variance cases.
Alpha keeps its original formula with corrected beta. Rounded constant-centering residuals,
uneven-scale recovery precision and other comparator statistics remain explicit limitations.
No epsilon, source repair, gate threshold, calibration identity or generated record changes.

ADR-269 identifies exact constants on both original aligned return Series before beta moments.
Either constant side yields beta zero, avoiding fabricated residual covariance from rounded
centering. Original native equality preserves wider distinct observations and partial overlap;
all nonconstant ADR-268 arithmetic and downstream formulas remain. Alpha naturally changes with
corrected beta. Near-constant/wide moment precision and other comparator statistics stay separate.

ADR-270 corrects the native wider nonconstant beta path with matched anchored centered sums
of original aligned values. Sample n-1 factors cancel; covariance/benchmark-deviation sums
remain native through division, then only final beta becomes float. Needed wider underflow
or an invalid denominator raises ValueError without a narrowed fallback; no unused strategy
variance is computed. Ordinary/nullable nonwide arithmetic and all other formulas remain.
Already-rounded sources, uneven translations, other statistics and native measurability limits
are not certified; thresholds, calibration identity and generated records remain unchanged.

ADR-271 supports genuine native wider returns paired with classic masked Float32/64 or
Int/UInt8/16/32/64 by subtracting original aligned native arrays into a plain wider excess
Series. Index and pandas binary name consensus are preserved using public empty ordinary
metadata operands. Every other pair retains pandas subtraction; guards and downstream
formulas remain. Arrow/Sparse/third-party support and universal numeric precision are not
claimed. No source repair, threshold, calibration identity or generated record change.

ADR-272 detects exact constants on original aligned excess before dispersion:
IR and tracking error are zero without rounded centering artifacts. Nonconstant
native wider excess uses anchored native sample variance/std retained through
the original IR quotient and tracking-error annualization. Needed native underflow
raises ValueError without narrowing fallback; final float tracking error can round
to zero while native dispersion still supports nonzero IR. Ordinary nonconstant
paths, mean, beta/alpha, excess metadata and drawdown remain. This is not universal
precision certification and changes no threshold, calibration identity or record.

ADR-273 subtracts both-original-unsigned native/classic masked integer sources
as exact Python integers before native floating excess encoding. Every encoded
integer ratio must equal the original exact difference or comparison refuses;
no wrap or silent rounding is permitted. Plain excess retains aligned index and
public pandas name consensus. All other subtraction/source/beta/alpha/drawdown
paths remain; IR/TE consume corrected excess through ADR-272. Derived excess
can be <=-1, since it is not a positive-wealth source return. Large original source
means/covariance and mixed signed precision remain separate limits; no threshold,
calibration identity or generated record changes.

ADR-274 additionally routes original mixed signed/unsigned native/classic masked
integer pairs through the same exact difference/certified encoding helper. Family
scope deliberately gives every mixed pair plain native floating excess, including
small pairs whose prior subtraction worked; IR/TE can change through ADR-272.
Both-unsigned ADR-273, signed-only and floating/native-wide paths retain exact
code/results. Original missing/negative source guards still precede subtraction;
derived negative differences remain valid. Source moments/beta/alpha/drawdown and
precision limitations remain; no threshold, calibration or generated record change.

ADR-275 computes beta for both-original-supported integer sources from exact
Python integer covariance sufficient sums, after original guards and exact
constant detection. Own-first deltas and streaming sums give exact
n*sum(ds*db)-sum(ds)*sum(db) over n*sum(db*db)-sum(db)**2 before one final
integer quotient to float. No native encoding/moments/scaled fallback is needed.
Integer beta rounding deliberately changes family-wide; original mean/alpha
formula remains, with alpha naturally using corrected beta. Noninteger paths,
excess/IR/TE/drawdown and source guards remain. Original means and other scalar
precision are not certified; no threshold/calibration/generated record changes.

ADR-276 uses the exact integer OLS intercept before beta/mean rounding for that
same integer domain: 252*(sumS*den-num*sumB)/(n*den) with one final float quotient.
Exact constant-source beta-zero convention uses only 252*sumS/n, bypassing all
covariance moments. Shared streaming sums preserve the beta wrapper; nonconstant
public pairs may scan twice without mutable caching. Integer alpha rounding
intentionally changes and need not match rounded published beta times rounded
means. Beta outputs, noninteger formulas, excess/IR/TE/drawdown and source guards
remain; no threshold/calibration/generated record changes or blanket precision claim.

ADR-277 matches classic masked Float32 benchmark variance to existing float64
covariance after integer/wider/constant precedence. Only that native denominator
uses a temporary plain float64 Series; needed existing scaled recovery uses both
original aligned float64 arrays for matched normalized moments. Original covariance,
scale restoration and other benchmark paths remain. Beta and its downstream alpha
may change; means/excess/IR/TE/drawdown and metadata stay. Float32 mean/dispersion,
large integer partner precision and uneven float64 normalization retain separate
limits; no threshold/calibration/generated record or universal precision claim.

ADR-278 extends that exact matched-precision path to native floating benchmarks
narrower than float64 (float16/32), preserving the old masked Float32 results and
all other benchmark/constant/integer/wider paths. Native narrowed variance can
overflow or underflow while covariance remains float64 measurable, producing
false beta-zero/same-series alpha. Both native variance and needed normalized
operands now match float64; covariance stays original. Means/alpha and narrow
excess moments retain separate limits, including zero risk from variance
underflow and float16/masked-byte-integer subtraction incompatibility. No threshold,
calibration identity, generated record or blanket precision claim changes.

ADR-279 measures nonconstant native float16/32 or classic masked Float32 EXCESS
with temporary float64 sample standard deviation (ddof1) and stable math.fsum
mean, retaining the original returned Series. Narrow variance can erase positive
risk or overflow; ordinary promoted summation can still erase a cancellation mean.
Exact constants bypass all new moments. Existing float64/wider/integer excess and
source beta/alpha/guards/drawdown stay unchanged. This intentionally changes narrow
IR/TE rounding, without epsilon or threshold/calibration/generated record changes.
Range bounds do not imply arbitrary correctly rounded moments; already rounded
subtraction, source alpha and masked-byte-integer compatibility remain separate.

ADR-280 calculates annual alpha for both-original native float16/float32 or
classic Float32 source pairs from exact Python integer sufficient sums on the
2**-149 grid. Only the final unrounded OLS intercept is converted to float;
constants keep beta-zero convention and use only the exact strategy total.
Published beta and accepted integer helpers remain unchanged. Narrow-family
alpha rounding intentionally changes and need not equal rounded beta times
rounded source means. Other source pairs, excess/moments/drawdown/metadata and
source guards remain. No threshold/calibration/generated record changes;
source beta precision and unsupported pairs retain their separate limits.

ADR-281 recovers collapsed/detected-underflow sample dispersion only for
nonconstant native float64/classic Float64 excess, retaining original nonfinite
std refusal and native finite arithmetic without detected underflow. Anchored
first-value deltas precede maxabs normalization; original fsum plus frexp/ldexp
separate IR from final annualized TE rounding. TE may legitimately round to zero
with nonzero IR. Constants and other excess families retain their paths. Exact
Fraction squared midpoint tests state a one-output-ULP subnormal property limit;
selected fixtures remain exact, without a universal correctly rounded claim.
Global lost-mean, source-alpha strict-state and original variance-overflow limits
remain separate; no threshold/calibration/generated record changes.

ADR-282 certifies a zero native mean only for nonconstant native float64/classic
Float64 excess with positive finite native std and no ADR-281 recovery. Original
fsum zero retains zero IR; a nonzero original total uses frexp/ldexp and the
EXISTING measured std, while uncertified overflow refuses. Tracking error stays
exactly unchanged. Nonzero native means, constants, other excess families and
ADR-281 recovery keep their paths. Fraction oracles use known native std and
state a one-output-ULP subnormal ratio limit, not exact variance or universal
correct rounding. No threshold/calibration/generated record changes.

ADR-283 computes both beta and annual alpha for both-original native float64/
classic Float64 sources from exact represented common-grid integer sufficient
sums, converting only final quotients. Exact constant-source beta0 uses only
the exact strategy mean. Final coefficient overflow refuses as ValueError;
legitimate rounded zero/subnormal results remain. Family-wide coefficient
rounding changes intentionally, and alpha uses the unrounded slope. Integer,
narrow, wider, third-party/mixed-other paths and original excess/IR/TE/drawdown/
metadata/guards remain. O(n) streaming scans avoid mutable caching; other
statistic precision/availability limits stay separate. No threshold, calibration
identity or generated-record changes; no historical contamination is established.

ADR-284 extends that coupled coefficient path to one original supported native/
classic integer source paired with native float64/classic Float64. Exact integer
ratios (int(value),1) preserve masked NumPy integer neighbors without float
conversion; original floating ratios and sufficient sums remain. Both-integer
ADR-275/276, both-Float64 ADR-283 and narrow/wider/third-party/mixed-other paths
retain their results. Mixed coefficient rounding changes family-wide, while
original excess/IR/TE/drawdown/metadata/guards remain. Already-rounded mixed
excess is a separate precision limit. No threshold, calibration or record changes.

ADR-285 additionally admits nativefloat16/32 orclassicFloat32 paired with
native/classic Float64 to that unchanged exact coupled coefficient helper.
Eligibility requires an original Float64 source and two supported native/
classic integer or float16/32/64 sources, excluding both-narrow, both-integer,
integer/narrow, genuine wider and third-party pairs. All predecessor coefficient
results and original other statistics/guards/metadata remain. Family-wide mixed
floating coefficient rounding changes; final overflow refuses and legitimate
zero/subnormal remains. Unrelated mean/excess/risk availability and precision
stay separate; no threshold, calibration identity or generated-record changes.

- `excess_returns = strat - bench`
- `information_ratio = sqrt(252) * mean(excess) / std(excess)`
- `beta = cov(strat, bench) / var(bench)`; `alpha = mean(strat) - beta*mean(bench)` (annualized)
- `tracking_error = sqrt(252) * std(excess)`
- `benchmark_relative_drawdown`: max drawdown of the **relative** equity curve
  `(1+strat).cumprod() / (1+bench).cumprod()` from a prepended unit baseline (a ratio — always
  positive). Do NOT compound the
  return *difference* (`strat - bench`); it can fall ≤ −1 and produce a meaningless curve.
  ADR-171 evaluates this same definition with per-period `log1p(strat) - log1p(bench)`, cumulative
  log wealth from a zero baseline, running log peaks, and `expm1(min(log_drawdown))`. Common
  growth cancels before accumulation, so overflowing standalone wealth cannot hide a later relative
  loss. No standalone/relative wealth curve needs to be exponentiated; extreme loss may round to -1.

**Oracle**: SPY vs SPY → excess≈0, IR≈0, alpha≈0, beta≈1.0 (ARCHITECTURE.md §8).
Never report an absolute Sharpe without benchmark context.

---

## 6. Monte Carlo (simulation/, NOT a strategy)

`app/research/simulation/monte_carlo.py`. GBM: `S_{t+1} = S_t * exp((mu - 0.5 sigma^2) dt +
sigma sqrt(dt) Z)`. Seeded RNG for determinism. **Invariant**: all path values > 0
(ARCHITECTURE.md §8 #8). Cite Black & Scholes (1973).

ADR-173 requires finite s0/mu/sigma/dt, positive s0/dt, nonnegative sigma, and finite drift/output
paths; unrepresentable upper arithmetic raises ValueError without a volatility cap. Positive
underflow flooring remains, at the true smallest float64 subnormal (`nextafter(0,1)`). ADR-123's
`finfo.tiny` is the smallest NORMAL, not smallest positive float, and overwrote subnormal starts.
The corrected floor preserves exact initial/flat-path price scale; unit-wealth risk losses below
either floor round to -1. Seeded GBM/cumulative-product math and loss thresholds are unchanged.

ADR-174 validates the risk estimator's supplied returns before fitting those same annualized
moments: at least two real nonboolean numeric observations, each finite and greater than -1.
Missing rows raise instead of being silently dropped; complete nullable numeric dtypes and
constant/zero series remain supported. The original complete Series feeds unchanged mean/sample
standard deviation, seeded GBM and loss comparisons. Index/timezone policy is unchanged; this
boundary does not certify iid/GBM assumptions or extreme summary-arithmetic stability.

ADR-175 preserves the native expected-terminal-return mean whenever finite and uses a
scale-normalized arithmetic mean only on intermediate sum overflow. Finite paths therefore
cannot produce an infinite expected return solely because their representable mean's sum
overflows. Paths, all observations, percentiles and loss comparisons remain unchanged.

---

## 7. ExperimentManifest (lineage)

`app/research/backtesting/manifest.py`. Frozen, JSON round-trips with ALL fields preserved
(§8 #10): `experiment_id` (UUID), `created_at` (UTC), `git_commit_hash`, `strategy_name`,
`parameter_hash` (SHA256 of sorted params), `data_source`, `symbol`, `start_date`, `end_date`,
`data_quality_report_id`, `adapter_version`, `validation_config_hash`, `benchmark_symbol`.
Without it, a backtest result is not a reproducible scientific claim.

ADR-137 makes this a production contract for new single-name StrategyLab rows rather than a model
used only by tests. A real-data hunt accepts a `ResearchDataset` only after `DataQualityEngine`
passes its exact vendor bars, then stores both that full report and a manifest for the selected
trial. The manifest shares the pool row's experiment UUID and links the embedded report UUID;
symbol, source, adapter version, request dates, code revision, selected parameter hash, and gate
configuration are fixed before the row is written. Legacy and synthetic rows remain explicitly
nullable because their vendor quality lineage cannot be reconstructed honestly.

ADR-138 uses a distinct `CrossSectionalManifest` for a multi-symbol claim. Shared fields bind the
experiment, selected strategy/parameter hash, validation config, executed revision, and equal-weight
universe benchmark. Its ordered `PanelComponentManifest` list binds each retained panel column to
one passed report UUID, source, adapter version, and requested range. The experiment embeds those
complete reports and validates that their ordered symbols exactly equal `universe_symbols`.

ADR-163 makes both manifest shapes authoritative before outer-experiment attachment. Creation is
timezone-aware UTC; Git and SHA-256 identities are full lowercase hexadecimal values; shared
identity is non-empty; symbols are normalized; acquisition ranges are ordered; and panel components
are defensively reconstructed into an immutable JSON-array-compatible list. Outer selected-trial and
quality-report links remain unchanged, as do acquisition and methodology.

ADR-139 extends the same real-data boundary to single-name forward testing. `manage_portfolio` and
paper target sizing require `ResearchDataset`, not a plain frame. Every newly computed
`ForwardScore` stores its `ResearchDatasetEvidence` (complete report, source, adapter version,
request range, and executed revision), and its report symbol must match the frozen position.
Provider/quality failures leave the prior managed score unchanged and yield no broker target;
legacy scores without evidence remain valid.

ADR-341 / FINDING-289 requires the complete canonical HTTPS paper-broker origin
after trailing-slash trimming. Substring matching allowed a paper hostname in
an unrelated URL component to bypass the initial destination guard. Canonical
and trailing-slash forms remain; HTTP, explicit ports, userinfo, paths, queries,
fragments and alternate authorities refuse. This validates the initial URL;
ADR-342 separately controls redirects. Inert
Request construction establishes the bypass, not an actual configuration,
credential exposure, external request or order. Request/reconcile math stays.

ADR-342 / FINDING-290 separately refuses automatic broker redirects through a
private HTTPRedirectHandler in a local default opener. Returning None preserves
native HTTPError/status/response body while preventing a follow-up request,
including same-origin redirects. Initial URL, method, payload, headers, timeout
and JSON decoding remain; default proxy/TLS/error handlers stay. Global urllib
opener customization is intentionally bypassed; explicit fetcher injection is
unchanged. Refusal may defer later orders/snapshot and cannot undo prior requests
or determine whether a server processed an order. Synthetic pipelines establish
the behavior, not an actual redirect/credential leak. No research identity changes.

ADR-339 separately requires the converted latest strategy weight to be finite
before its existing [-1,1] clamp. Python min/max could turn NaN into a full short;
nonfinite output now raises before quote/target completion. The existing broker
orchestration propagates that refusal, aborting the whole target calculation
before reconciliation rather than skipping the name or inventing a zero target.
Finite conversions/clipping, earlier warmup history, ADR-120's NaN-price-to-flat
policy and sizing arithmetic remain. Source quality alone does not certify
computed weights. No affected actual catalog output or paper order is established
(FINDING-287); no threshold, search identity or accounting-v14 change.

ADR-340 / FINDING-288 requires finite inspection and a nonnegative original
equity operand at `equal_weight_targets`, before active counting or shortcuts.
Negative capital could reverse a frozen signal's direction; invalid capital now
raises even for empty/flat/invalid-price books. Zero/signed zero, original native
allocation arithmetic and ADR-120 price behavior remain. Native inspection errors
propagate; no arbitrary-precision recovery or new scalar-type contract is added.
The refusal propagates before reconciliation and the later equity-snapshot append,
so it also defers potential flattening and does not guarantee insolvency recording.
ADR-169 account/ledger models still admit negative observations. No actual negative
account, affected target/order, threshold, search identity or v14 change is established.

ADR-164 makes `ResearchDatasetEvidence` revalidate instantiated inputs, including unchecked copies,
before direct validation or attachment to either forward-score model. Acquisition bounds must be
timezone-aware and normalize to UTC. `ResearchDataset` shares this identity boundary and retains
the validated report snapshot before its frame checks. Existing JSON shapes, quality rules, and
legacy absent evidence remain unchanged; mutable frame ownership and outer-score copies are
separate audit surfaces.

ADR-140 applies panel semantics to cross-sectional forward testing. The managed-book provider must
return one `ResearchDataset` per frozen universe symbol; exact membership, report symbols, common
revision, and post-alignment columns are checked before the factor or equal-weight benchmark is
computed. Any failure defers the entire position update instead of scoring a different subset.
New `CrossSectionalForwardScore` rows carry the ordered complete component evidence; legacy and
direct synthetic scores may retain `None`.

ADR-363 extends ADR-252's direct scoring column contract to direct cross-sectional
lifecycle evaluation: after policy revalidation and before calendar access or
no-forward holds, require the exact frozen ordered columns. Subsets, substituted,
extra or reordered labels refuse without normalizing or repairing the panel.
The managed book already enforces this identity. Matching-panel arithmetic,
grace, reasons, defaults and thresholds remain; no broader calendar/price or
position-reconstruction rule is introduced (FINDING-303).

ADR-364 requires original source indexes to be unique and ascending at the raw
panel score and both raw lifecycle wrappers before calendar access/no-forward
shortcuts. Policy/column and early evidence reconstruction/frozen-symbol checks
retain precedence; score-root common-revision validation remains later.
This mirrors engine calendar identity without invoking extra price/strategy work,
sorting, deduplication or UTC/cadence coercion. NaT fails the native ordering
predicate. Empty/naive lifecycle holds and existing empty/naive score refusals
remain; generic timestamp-object/offset calendars retain their prior behavior.
No measured noncausal return or affected actual book is established (FINDING-304).

ADR-142 freezes the panel-projected value and quality score mappings on every new cross-sectional
experiment because those static fundamental inputs define the `xs_value`, `xs_quality`, and
`xs_quality_value` trials just as prices do. Promotion copies only those historical snapshots into
the forward position, and registry reconstruction supplies both. A legacy fundamental graduate
without its required snapshot is left unpromoted rather than rebuilt from a later fundamentals pool.
ADR-143 closes the nested-mutation and non-finite-input gaps at both experiment and position model
boundaries: snapshots are defensive immutable copies whose finite keys must follow frozen universe
order, while JSON remains an object and retains `None` plus absent-key semantics.
ADR-144 also deep-freezes the forward position's reconstruction parameters and ordered universe.
Their JSON shapes remain object and array, but in-place mutation can no longer redirect factor
scoring, lifecycle evaluation, or panel evidence validation under an existing position identity.
ADR-145 applies the corresponding complete boundary to `CrossSectionalExperiment`: ordered
universe/strategy collections, trials and parameter maps, graduate, gate verdicts, panel manifest,
and embedded quality evidence are defensively reconstructed and recursively immutable. JSON keeps
the existing object/array schema, while reload revalidates selected-trial, graduate, gate, and
lineage relationships as one claim.
ADR-147 applies that complete boundary to the single-name `Experiment` as well. Ordered trials,
parameters, graduate and gate verdict, fundamental and valuation evidence, manifest, and embedded
quality report are defensive immutable copies. Construction and reload bind the selected trial to
the graduate and manifest, preserve ADR-079's legacy max-DSR fallback, and reject mismatched symbol
or veto evidence without changing JSON object/array shapes.
ADR-160 hardens the shared `GateResult` before it reaches either experiment graph. Its persisted
`passed` value must equal the six-component conjunction, reasons are immutable JSON-shaped evidence,
MinTRL/config identity is valid, and structured holdout fields are paired. Positive infinity remains
the defined requirement for a non-positive observed Sharpe. The probability-DSR comparison's
artifact reconstruction closes unchecked-copy inference without changing gate policy.
ADR-162 applies the same standalone boundary to the shared `Trial` and `Graduate` leaves. Parameters
are immutable JSON mappings, scalar evidence is finite and range-valid, and a graduate must carry a
passing gate plus positive, matching structured holdout geometry. Longitudinal and cross-sectional
whole-search repricing reconstructs the concrete trial subtype through validation instead of an
unchecked model copy. No statistic, selector, gate predicate, threshold, or persisted JSON shape
changes.
ADR-148 extends the boundary to `PaperPosition`: parameters, lifecycle reasons, forward curves, and
nested score evidence are defensive immutable copies. Construction, managed updates, reload, and
store writes validate lifecycle identity, evidence symbol, count/finite constraints, and any
non-empty curve's ordering and terminal returns. Legacy empty curves and evidence-null scores remain
readable.
ADR-149 applies the complete boundary to `CrossSectionalPosition`. Lifecycle reasons, score curves,
and ordered component evidence join the already-frozen reconstruction fields as defensive immutable
copies. Construction, managed replacement, reload, and store writes validate open/retired state,
finite cost and statistics, unique universe identity, evidence order/common revision, and non-empty
curve geometry. Evidence-null scores and empty curves remain supported.
ADR-150 closes the durable-write bypass for experiment pools. Monolithic and partitioned
single-name writers and the cross-sectional writer reconstruct all incoming model dumps through the
ADR-145/147 boundaries before any filesystem mutation. Retention, deduplication, and lifetime-trial
accounting are unchanged.

ADR-155 applies the same durable-boundary rule to the independent fundamentals pool that supplies
cross-sectional value and quality inputs. `FundamentalRecord` flags are defensive immutable copies;
quality/value/combined scores are finite in `[0, 1]`, F-score is in `[0, 9]`, and combined equals
quality times value exactly when both legs exist. Merge reconstructs every input record before
newest-filing deduplication, closing unchecked-copy writes without changing factor formulas or JSON
array/object shapes.

ADR-156 closes the equivalent root-boundary gap in `DataQualityReport` itself. Issue order and nested
context evidence are defensive immutable copies, context is finite JSON data, and both repository
writers reconstruct unchecked model copies before retaining or transacting. Embedded reports thus
keep one verdict and provenance under one UUID without changing checks, thresholds, or JSON shapes.

ADR-152 makes `paper-forward.yml` the sole production workflow writer of the single-name paper
portfolio. Discovery and hunt workflows persist research-pool evidence only; `scripts/paper.py`
loads the complete committed pool and idempotently promotes all eligible graduates on its next
daily run before updating open-position lifecycle evidence. Do not restore portfolio staging to a
search workflow or try to serialize unrelated workflows with one lossy GitHub concurrency group.

ADR-153 causally orders broker reconciliation after that writer. Automatic paper-broker runs are
triggered only by successful completion of `Paper forward accrual`, then explicitly read current
`master`; a clock offset is not a dependency. Manual broker recovery follows the same checkout
rule. Failed accruals must not place automatic paper orders.

ADR-154 makes daily discovery the sole automated publisher of `data/research_pool`. The retired
weekly workflow searched only a subset of the weekday discovery universe and could conflict on the
same generated symbol partitions from a stale base; its local fallback could leave a divergent
commit after push rejection. Custom/recovery sweeps use daily discovery's manual universe input.
Do not restore another automated commit/push path for the research pool.

---

## 8. Oracle tests (must pass before any Phase 4 validation)

A sophisticated statistic on a buggy engine is worthless. All in `tests/`:
- `buy_and_hold_matches_analytic`: 100%-long signal → equity matches closed-form
  `initial * close/close[0]` (within 1e-9, zero cost).
- `zero_signal_produces_zero_exposure`: all-zero signals → flat equity, 0 trades, 0 Sharpe.
- `symmetric_long_short_neutrality`: +1/−1 alternating in a trend nets ≈ 0 (costs only).
- `transaction_cost_reduces_returns_monotonically`: costs=[0,.001,.005,.01] → returns non-increasing.
- `benchmark_comparator_spx_baseline`: SPY vs SPY → excess≈0, IR≈0, alpha≈0, beta≈1.

ADR-165 gives `ResearchDataset.frame` defensive ownership. Construction captures a private numeric
OHLCV snapshot; each access returns an independent working frame, explicitly copying both axes
because ordinary pandas deep copies can share datetime-index storage. Source and returned-frame
edits cannot change the retained observations under the same quality identity. Constructor
`frame=` and `dataclasses.replace` remain supported. Arbitrary mutable object-valued cells are
outside the canonical numeric frame contract; direct supplied report/frame correspondence is not
certified by this ownership boundary.

ADR-166 makes standalone forward points/scores authoritative intrinsic evidence boundaries.
Both point families require aware UTC timestamps and finite positive equities. Both score families
revalidate instances, require aware UTC cutoffs, finite statistics and valid counts, freeze curve
lists, and bind nonempty curves to length, chronological order, terminal returns, and `as_of`.
Single-name trades cannot exceed bars; present panel evidence is immutable, nonempty, symbol-unique,
and at one revision. Position boundaries still bind symbol/universe and freeze-date identity.
Legacy empty curves, absent evidence, and historical beats flags remain supported.

ADR-167 validates direct `ResearchDataset` capture as canonical numeric research input: unique flat
columns including `close`, real nonboolean numeric finite values, positive present OHLC with
pairwise low/high bounds, nonnegative optional volume, and timestamps in the evidence's half-open
request range. Close-only frames, complete nullable numeric columns, aware offset calendars, and
finite signed auxiliary features remain valid. Object/complex/string payloads are rejected rather
than coerced. These structural guards do not prove a direct frame/report pair underwent quality
checks; production acquisition must still use checked PriceBars through preparation.

ADR-168 validates lifecycle inputs before grace/no-trade/no-forward holds. Both exit policies
revalidate instantiated inputs and reject nonfinite scalars, negative grace/drawdown, and nonpositive
rolling windows; the single-name no-trade horizon is positive. All defaults and predicates remain
unchanged, including support for finite negative Sharpe floors and drawdown limits above one in
diagnostic configs. Pure lifecycle functions require exactly aligned, unique ascending paired
numeric returns, finite and greater than -1, plus a valid single-name trade count. Aligned empty
history and naive/generic indexes remain valid. Input validation does not certify arbitrary extreme
floating-point compounding/variance arithmetic.

ADR-356 includes pre-return unit wealth in both lifecycle drawdown histories,
after grace and single-name no-trade branches. The baseline has the existing
compounded equity's dtype; original cumprod and peak-to-trough arithmetic remain.
An initial forward loss can now trigger the unchanged strict risk limit even if
later recovery makes rolling Sharpe healthy (FINDING-296). Policy defaults/hashes,
rolling statistics, reason text, score/curve schemas and generated records stay;
the internal baseline adds no persisted bar or timestamp. Historical decisions
are not restated, and extreme native compounding remains a separate limitation.

ADR-361 distinguishes absence of turnover from absence of forward return evidence.
The single-name no-evidence branch now requires both zero forward trades and every
validated original forward return exactly zero. A warmed config may remain long
or short after freeze with no position changes while earning nonzero returns;
those paths face the unchanged risk/performance rules after grace. The forward
score permits its unchanged strict Sharpe benchmark comparison when there is
turnover or any nonzero forward return, retaining the actual zero trade count.
No epsilon, sum/product shortcut or invented entry trade is used. Genuine
all-zero/no-trade holds/timeouts, defaults, policy hashes, arithmetic, reasons
and schemas remain. All-zero returns cannot prove flat exposure; observed returns
do not attest account entry or reconcile execution/switching costs. Historical
data/decisions stay intact. See FINDING-301 and its public default-Momentum witness.

ADR-169 gives the separate broker account ledger (`execution/equity_curve.py`) an intrinsic point
and chronological-batch boundary. Points require aware UTC times, finite scalars, strict
nonnegative integer counts, and jointly measured/absent benchmark-alpha fields. Load/save/append
reconstruct all points and enforce increasing times; writers validate and serialize before filesystem
changes. Nominal/inception denominators must be positive where measured. Actual zero/negative equity
and negative cash remain honest account observations; historical alpha formulas and custom nominal
baselines are never guessed or restated. This ledger is distinct from positive normalized research
wealth curves and does not authorize broker access or generated-data edits.

ADR-170 anchors prospective broker SPY benchmarks to completed New York regular daily closes
associated with each observed account endpoint, fetching fourteen calendar days before inception
through ResearchDataset quality gates. Midnight session labels alone do not prove close availability.
Weekday regular-hour snapshots are unmeasured; before open use the preceding weekday, after 16:00
use today, and weekends use Friday. Exact expected date anchors are required: holidays/missing bars,
unsupported labels, failed quality/fetches, and unrepresentable float ratios produce absent benchmark
and alpha. Early closes are conservatively unavailable until 16:00; an intraday inception cannot
establish this proxy at all. The first snapshot is unmeasured; identical completed-close endpoints
yield zero. Account endpoints remain observed marks, so this proxy is not exact intraday/after-hours
attribution. Existing ledger values and ADR-141's account denominator are not restated.


### AR reference identity (ADR-308)

PowerCalibration and PowerSweep retain optional nullable `ar1_reference`. The
frozen/revalidated closed object distinguishes legacy phi-lag sign (null drift)
from conditional-mean sign (explicit finite original nonboolean Real drift).
Known-reference cells require AR edge and phi; conditional cells require
stationarity. Sweep headers bind edge/reference and centrally require the same
reference identity in every cell, including reconstructed unchecked copies.

Conditional measurement dispatches gross/net to the unchanged ADR-223 helper;
default scorer/source/search calls remain. New ordinary phi+ar1 default results
record known legacy method; historical missing metadata and externally scored
arrays stay unknown. Odd legacy custom-edge phi remains unknown. Reject explicit
contradictions before scoring/search. Collector and capture comparisons cannot
mix denominators; detection-only joint-count semantics remain unchanged.
No search/gate threshold, fingerprint/accounting-v14, source or artifact rewrite.

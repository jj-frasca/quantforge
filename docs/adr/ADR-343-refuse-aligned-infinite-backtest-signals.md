# ADR-343: Refuse aligned infinite backtest signals before clipping

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 15, ISO 2026-W43; independent research review
- **Resolves:** FINDING-293
- **Extends:** ADR-007/176/177/178
- **Related:** ADR-260/265/339

## Context

BacktestEngine.run aligns signals to the price index, clips weights to [-1,1],
then fills missing weights with zero. Signed infinity is erased by clipping
before finite-equity checks: supplied prices[100,110,121], signals[+Inf,0,0]
and cost_rate=.001 produce position[1,0,0], finite equity and total return
.09790100000000002. Negative infinity produces a full short and total return
-.10189900000000007. These are deterministic direct-engine fixtures, not
observed catalog outputs, historical corruption or market performance claims.

Missing signals have an existing deliberate meaning: warmup NaN/pd.NA and gaps
introduced by reindex become flat. Finite out-of-range weights intentionally
saturate. ADR-339's latest-paper-signal policy refuses every nonfinite converted
last value; copying it wholesale would change these backtest semantics.
ADR-260/265 supply related infinity-only precedent at different cross-sectional
boundaries, but refuse original observations rather than only aligned rows.

## Options considered

1. Refuse exact signed infinity in the already aligned signals before clipping.
   - Pro: prevents invented full exposure while retaining missingness, finite
     clipping and the established discarding of unmatched labels.
   - Con: unmatched invalid observations remain unvalidated; final/singleton
     aligned infinity aborts even without a following held-price return.
2. Refuse infinity anywhere in the original signal Series before reindex.
   - Pro: stronger original-source contract, consistent with ADR-260/265.
   - Con: changes existing behavior for discarded unmatched observations and
     empty price histories beyond the aligned-exposure defect selected here.
3. Refuse all nonfinite weights or impose a broad dtype/range validator.
   - Pro: broader intrinsic source contract.
   - Con: changes deliberate NaN/pd.NA warmup, finite saturation or currently
     unsupported-input behavior; requires a separate scope decision.
4. Keep infinity saturation or turn infinity into zero/missing.
   - Pro: preserves completion or permits continued calculation.
   - Con: invents full or flat exposure from invalid strategy evidence.

## Decision

After the original price-calendar, price-dtype and price-value checks, retain
the original returns calculation and bind `signals.reindex(prices.index)` once.
Before clipping/filling, require that this aligned Series has no exact signed
infinity under native `isin([np.inf, -np.inf]).any()` membership; otherwise raise
ValueError. Apply the original `.clip(-1.0,1.0).fillna(0.0)` to that same aligned
Series for accepted calls. Add no float64 conversion, dtype ban, strict finite
range rule, filling/dropping policy or NumPy error-state change.

Preserve native finite values, including explicitly typed float128 values
outside binary64 range, integer/nullable integer and float32 controls. Preserve
signed zero, fractional conviction, finite saturation, NaN/pd.NA warmup, sparse
alignment, unmatched labels and empty results. Unmatched infinity remains
discarded; this is deliberately an aligned-observation contract, not validation
of every supplied source leaf or proof of strategy causality.

Refuse aligned infinity even at the final bar, on a singleton, or with zero
cost. An absent subsequent holding period does not make that aligned weight
valid. Preserve original malformed-price/calendar error precedence. Native
membership also matches Decimal Infinity and complex(inf,0): those audited
unsupported fixtures already failed, but now receive the guard's ValueError
earlier. Do not promise identical message/timing or warnings for flagged
unsupported inputs. Unflagged unsupported type errors retain the native path.

## Consequences and verification

Formerly successful aligned-infinity calls become refusals. If such a call is
encountered by search/calibration, it may become a recorded error or abort its
caller and change the completed denominator. Inspect the actual callers before
claiming a particular orchestration outcome. Unchanged finite formulas do not
establish unchanged historical or future rates. No actual affected production
result, graduate, source law or rate is established, and no frozen cohort is
replayed, relabeled or regenerated.

Retain all accepted finite arithmetic, metrics, lag/turnover/cost/equity
expressions, fields, thresholds and accounting-v14 estimator identity. The
existing search/gate fingerprints are intended to remain unchanged and must be
verified; edited engine source provenance changes and must be stated separately.
No new rate claim follows from fingerprint equality.

Independent scratch proposal audit checked 28 supplied-signal cases plus four
boundary controls. It compared complete position/return/equity Series including
dtypes, metric objects, n_trades and cost_rate for unflagged accepted cases, and
exception type/message for unflagged refusals. Explicit native-wide finiteness
was asserted before the engine. This is not repository TDD or a completed gate.

Before implementation, observe meaningful refusal RED for both signs and
aligned first/interior/final/singleton, nullable and native-wide observations.
Preserve missing/sparse/finite saturation and original source-error precedence;
include bounded finite/missing compatibility properties without narrowing
existing oracle or monotonic-cost domains. Verify untouched executable AST
outside the declared reindex binding, infinity guard and position operand;
compare accepted finite complete payloads to the prior implementation. Add the
necessary standard NumPy reference only if absent (it is already imported here).
Require independent final review, foreground make check-all and exact pushed CI.

## Reversal

Remove the aligned infinity guard and restore the original inline reindex/
clip/fill expression. This restores the finite-publication defect in F293.
Changing missingness, original-source validation or failure policy requires a
separate explicit decision rather than silently manufacturing exposures.

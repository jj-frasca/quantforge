# ADR-353: Measure runtime-attributed Alpha4 purged diagnostics

- **Status:** Accepted
- **Date:** 2026-10-23
- **Deciders:** Codex autonomous session22, ISO2026-W43
- **Extends:** ADR-325/348/350/351/352
- **Addresses in part:** FINDING-265; preserves FINDING-272

## Context and source evidence

ADR-352's distinctly attributed Alpha4 readers are individually published and
exact master CI green. Its actual producer remains unsupported. Independent
source and deterministic endpoint/oracle review supports a restricted recipe.

The actual ts_rank path is rolling.apply(raw=True) with a fresh callback
float((s<=s[-1]).mean()), not pandas Rolling.rank. The reviewed
[pandas3.0.6 roll_apply](https://github.com/pandas-dev/pandas/blob/v3.0.6/pandas/_libs/window/aggregations.pyx#L1421-L1455)
passes each arr[start:end] independently. Its rolling admission sum sees finite
indicators identically1 on this complete finite price domain, independent of
price magnitudes; small counts<=21 are exact. No previous callback score or
price-valued accumulator enters the next callback. The reviewed NumPy2.5.4
_core/_methods.py _mean sums a fresh boolean vector in Float64 then divides by
window length. Counts<=21 are exact and rounded fractions depend only on the
current window. This does not generalize to arbitrary callbacks, missing/inf
inputs, other builds/versions/engines, monkeypatches or concurrent mutation.
FINDING-272's price-valued rolling-sum/variance limitation remains valid.

The signal hull is [t-W+1,t]; previous weights/current turnover extend net
returns to [t-W,t], D=W. Shipped windows are5/9/21. Operative <= tie fixtures
change oldest price t-W, previous holdings, gross and turnover while current
weights stay exact. Whole expired-prefix changes leave current operands exact;
current-price changes leave earlier outputs exact. Callback/window and prefix
oracles match, ties count fully, W-1 signals remain NaN and first entry pays
cost. E=W-1 shares a source price at both train/test boundaries; E=W separates
them. Bounded controls supplement the derivation, not independence/calibration.

## Decision

Support only exact xs_alpha4/alpha4_factory identity, native Float64 complete
positive panels and allocated nonboolean Integral windows5/9/21. Use D=max(actual
allocated W), E=max(original floor,D), without shrinking. Reuse unchanged matrix,
evaluator and actual family-kept-fold equal-weight benchmark. Measured/no-fold
outcomes use ADR-352's exact v4/rolling-alpha4-percentile-v1. Existing high-v2,
Alpha9-v3 and shifted-v1 evidence, signals and primary formulas remain unchanged.

Add a dedicated frozen Alpha4Runtime carrying observed pandas version, NumPy
version and standard engine option, with its own capture helper and saved slot.
Preserve HighRuntime and its high/Alpha9 API/behavior. At each exact known Alpha4
allocation key/name/factory _config_returns, capture immediately before/after,
requiring agreement within a call and across that family's configs. Carry its
receipt with its matrix; separate families may have different domains. Preserve
unrelated-key short-circuit for manual/custom stubs. Do not force an engine or
change a global option. Missing/wrong known-Alpha4 receipts and inconsistent
observations raise; replaced same-name factories remain unsupported_factory.

Actual measurement classifies only the saved Alpha4 receipt, never later globals
or a HighRuntime lacking NumPy identity. Pure support queries may observe current
domain. Only pandas3.0.6/NumPy2.5.4/use_numba=False supports this reviewed recipe.
Other pandas/NumPy/engine domains remain v1 unsupported with existing reasons
plus unsupported_numpy_version. Extend backend/API/client reason readers and
plain-language display coherently. Primary eligibility stays for unsupported
domains; no scores or v4 attribution are invented. Receipts are bounded metadata,
not hostile-code provenance or binary-build attestation. Classify pandas first,
then NumPy, then engine. Numerical evaluator errors continue propagating.

Explicitly supersede ADR-351/352's blanket actual-Alpha4 unsupported assertions
with audited support and unaudited-NumPy refusal. Supersede reader-only tests
that excluded Alpha4 from the support caption, retaining the stronger check
that historical rows receive no invented fold qualification. Retain every test
and all other assertions. Update support caption and cold memory without
relabeling historical evidence. All noncausal
training, whole-sample family selection, mean-of-Sharpes, internal configuration
costs/no account-switching reconciliation, no extra benchmark turnover costs,
PIT/universe and absent panel-calibration limits remain. No threshold, selector,
primary arithmetic, fingerprint, longitudinal-v14 or generated/frozen record
changes. New measurement refusals may change completion domains, not thresholds.

## Alternatives and reversal

HighRuntime cannot attribute NumPy; silently reusing it is insufficient. Late
NumPy checks misattribute execution, and forcing engines changes primary
semantics. Broad version-independent callback certification is unreviewed.
Choose the dedicated captured first domain. Reverse Alpha4 support/capture only,
retaining published readers, findings and all historical generated records.
Further runtime/scientific domains require their own reviewed decision.

## Verification

Observe backend/reason-client/rendered RED before implementation. Test original
domain and allocation/floor counts, missing/wrong/custom receipts, before/after
and cross-config drift for all observed identities, saved-safe/unsafe versus
later globals, independent family slots, exact allocated maxima, actual kept-fold
benchmark, no-fold/large-floor and numerical refusal. Fake unsafe metadata only;
never execute Numba or mutate engine globals. Hypothesis covers operative hull
locality and both embargo endpoints; preserve callback/ties/warmup and stable
factory semantics. Preserve full primary/WF/gate/accounting payloads except
intentional trial-PCV and UUID/time, existing high/Alpha9/shift evidence, unrelated
AST/data bytes and fingerprints. Independent research/frontend review, fresh
foreground make check-all, explicit-path commit, safe fresh sync, individual
immediate push and exact master CI precede completion. No calibration/cohort/
provider measurement is authorized beyond deterministic synthetic unit fixtures.

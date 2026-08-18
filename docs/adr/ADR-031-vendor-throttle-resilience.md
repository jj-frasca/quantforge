# ADR-031: Vendor throttling is a first-class failure mode — backoff, throttle, and a yield floor

- **Status**: Accepted
- **Date**: 2026-08-18
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-015 (yfinance as the research data source), ADR-026 (maximum token-free discovery)

## Context
The daily discovery matrix (ADR-026) is the engine of this project: ten parallel shards hunt the
610-name discovery universe with the full strategy catalog every weekday. On 2026-08-18 it was
found to be **green and doing nothing**.

Evidence, both runs on 2026-08-18:

| run | outcome | symbols | experiments | errors |
|---|---|---|---|---|
| `32118015639` (08:45) | **success** | 610 | **4** | **606** |
| `32097156994` (03:54) | success | 610 | 278 | 332 |

Every error is the same: `yfinance.exceptions.YFRateLimitError: Too Many Requests`, raised from
`YfData._get_crumb_basic` — the *session bootstrap*, not a per-symbol quota. Yahoo throttles the
shared GitHub-runner egress IPs. Yield swings between ~45% and 0% depending on how hot the runner's
IP is that hour.

Two independent defects made this invisible and unrecoverable:

1. **No loudness.** `b2b7f5a` correctly normalized vendor errors to `OSError` inside the adapter so
   one bad symbol cannot kill a whole shard. `run_universe_hunt` then records and skips it. The
   consequence nobody designed for: a shard where *every* symbol failed still exits 0 and the
   workflow is green. Before that commit the job at least went red — there are seven consecutive
   `Daily discovery (sharded)` failures 2026-08-10..18. **Green-but-empty is strictly worse than
   red**: red is a signal, green-but-empty is a silent rot that would have burned weeks of the
   experiment before anyone noticed the pool had stopped growing.
2. **No backoff anywhere.** There is not a single retry or sleep in the fetch path. One 429 drops a
   symbol for the entire day. Worse, because the throttle hits the *crumb bootstrap*, the first
   symbol's failure is the same failure every later symbol gets — 61 symbols fail in ~90 seconds,
   the whole shard wiped out by one hot minute on the runner's IP. The workflow's outer
   `for attempt in 1 2; ... sleep 30` retry is far too coarse to help: it re-runs the entire shard
   after 30s, still inside the same throttle window.

The project's stated value is that its reporting is honest. A pipeline that reports success while
producing nothing is the same class of dishonesty as a gate that manufactures graduates.

## Decision

**Treat vendor throttling as an expected operating condition with three layers, not as an error.**

### 1. Bounded retry with exponential backoff and jitter, at the adapter
`app/data/sources/retry.py` provides a `RetryPolicy` (attempts, base delay, max delay, jitter) and
a `retrying` helper. `YFinanceAdapter` takes an optional `retry: RetryPolicy`, defaulting to
`RetryPolicy(attempts=1)` — **no behaviour change for existing callers or tests**. Only a retryable
failure (the `OSError` the adapter already normalizes vendor errors into) is retried; `ValueError`
and `KeyError` are *data* verdicts, not transient, and are re-raised immediately.

Backoff is exponential with full jitter (`sleep ~ U(0, base * 2^n)`, capped). Jitter matters here
specifically: ten shard jobs start simultaneously against one vendor from neighbouring IPs, so a
fixed schedule would synchronize all ten retries into the same instant and re-trigger the throttle.

This is the layer that *recovers* a wipeout: once any one call gets past the crumb bootstrap,
yfinance caches the crumb on its `YfData` singleton and the rest of the shard proceeds normally.
Retrying the first symbol for ~a minute buys back the whole shard.

### 2. A polite inter-request throttle in the cloud drivers
`RetryPolicy` also carries `min_interval` — a floor on the gap between successive fetches, enforced
by the adapter. The cloud drivers (`shard_hunt.py`, `cross_sectional_hunt.py`) set it; local and
test callers leave it at 0. Sixty symbols at a 1.5s floor costs ~90s of wall clock on a job with a
350-minute budget and unlimited Actions minutes. Not being throttled in the first place is much
cheaper than recovering from it.

### 3. A yield floor that fails the shard loudly
`shard_hunt.py` exits non-zero when the fraction of its symbols that actually produced an experiment
falls below `min_yield` (default **0.25**). A shard is a *sample* of the universe; below a quarter
coverage it is not a thin day, it is a broken fetch, and the run must say so.

0.25 is deliberately a low bar. The observed "good" run had a 54% error rate (46% yield) and did
real work — failing that would be crying wolf. The bar exists to catch wipeouts (0–7% yield), not to
police normal vendor flakiness. The number is a knob on the driver, revisable from observed yields.

**This threshold governs data acquisition, not validation.** It is not a graduation criterion and it
can never make a strategy pass; the DSR/PBO/MinTRL gate is untouched by this ADR.

## Alternatives considered

- **Leave it green and skip silently.** Rejected: this is the status quo, and it is how the loop
  died unnoticed.
- **Fail on *any* symbol error.** Rejected: delisted tickers, ETFs with no 10-K, and short-history
  IPOs fail every single day by design. This is the behaviour ADR-026 already had to abandon.
- **Retry inside `_download_yf` only.** Rejected: the normalizer's parse errors (`b2b7f5a`) surface
  at the same boundary, and retrying at `fetch_price_bars` keeps *one* place where "transient vendor
  failure" is defined.
- **Batch `yf.download(tickers=...)`.** Rejected for now: it shares one session (helpful), but it
  fails as a *unit* — one throttled response loses the whole batch and destroys the per-symbol
  resilience `run_universe_hunt` is built on. Reconsider only if per-symbol backoff proves
  insufficient.
- **A second vendor (Stooq / Alpaca) as a cloud fallback.** Genuinely attractive and *not* rejected —
  it is simply larger, and a second vendor with different adjustment conventions silently changes
  what the research pool means. Deferred to its own ADR, to be judged on the yields this change
  produces. Alpaca's free IEX history is too short for MinTRL (ADR-015), so the candidate is Stooq.
- **Self-hosted runner on Joe's machine.** Rejected: costs Joe's hardware and availability, and the
  charter forbids spending money or taking on operational burden he has to babysit.

## Consequences

- Shards get slower (roughly +2–4 minutes each) and much more likely to return data.
- A genuinely throttled day now goes **red** and emails Joe, instead of quietly reporting success.
  That is the intended trade: a false alarm costs an email, a silent no-op costs weeks of experiment.
- `RetryPolicy` is vendor-agnostic and reusable by the EDGAR source if the SEC starts 429ing.
- CI is unaffected — it never touches the network, and the default policy is a single attempt.

## Reversal
Delete `app/data/sources/retry.py`, drop the `retry` argument from `YFinanceAdapter`, and remove the
`min_yield` check from `shard_hunt.py`. Nothing else depends on them; the defaults are the old
behaviour, so reverting the drivers alone restores the previous operating characteristics.

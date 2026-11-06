# FINDING-350: `xs_quality` dominates cross-sectional selection 11/11 times eligible; blocked by MinTRL at the margin, not comprehensively

- **Status:** Open
- **Date:** 2026-11-06
- **Discovered by:** Interactive session (Joe present), reviewing `data/cross_sectional_pool.json`
  after redirecting both autonomous charters toward the quality/value research thread.
- **Relates to:** ADR-024 (cross-sectional engine), ADR-029 (fundamentals division),
  ADR-046/ADR-104 (lifetime-trial DSR/PBO denominator), ADR-060/063/068-078/094 (the single-name
  technical-search results this finding stands in contrast to).

## What was measured

`data/cross_sectional_pool.json` holds 30 cross-sectional experiments. Only 11 of them had
`quality_scores`/`value_scores` populated at search time (the rest predate sufficient
`fundamentals_pool.json` coverage, or ran on a universe slice with none scored). Restricted to
those 11:

**`xs_quality` won the cross-family selection 11/11 times** — every single time it was eligible to
compete, it beat momentum, reversal, low-volatility, and every alpha-N price-only factor in the
registry. This is a categorically different result from the single-name technical search, where
ADR-060 measured the selection step as barely distinguishable from noise (a winning family's lead
over the runner-up was +0.079 Sharpe against a standard error of 0.22 — a third of one SE).
`xs_quality`'s 11/11 record is not that: it is a clean, repeated, unambiguous win.

**It still does not graduate — but by a measured, narrow, specific margin, not a wall.** Every one
of the 11 winning experiments fails the gate on exactly the same two checks, every time:

| `lifetime_trials` (N) | `xs_quality` observed Sharpe | MinTRL years required |
|---|---|---|
| 2,052 | 0.684 | 32.6 |
| 2,187 | 0.825 | 22.6 |
| 2,322 | 0.810 | 23.6 |
| 2,457 | 0.918 | 18.5 |
| 2,592 | 0.936 | 18.0 |
| 2,727 | 0.729 | 29.8 |
| 2,862 | 0.737 | 29.3 |
| **2,997** | **0.957** | **17.5** |
| **3,132** | **0.960** | **17.5** |
| 3,267 | 0.751 | 28.7 |
| 3,402 | 0.762 | 28.0 |

(Computed directly from `app.research.lab.gate.minbtl_years(n_trials, observed_sharpe)` — the
Bailey/López de Prado `2·ln(N)/SR²` approximation this project already uses everywhere else.)

`dsr_ok` and `mintrl_ok` are `False` on every row; `pbo_ok`, `stability_ok`, and `holdout_ok` are
`True` on every row, no exceptions. PBO ranges as low as 0.012 (far inside the 0.5 threshold) on
the sampled trial. This is not a strategy that is marginal on everything — it is specifically and
only blocked by the selection-penalty accounting (DSR, which is itself driven by the same MinTRL
inputs).

**The best two rows (N=2,997 and N=3,132, Sharpe ≈0.957–0.960) require 17.5 years of track
record.** The panel's actual available in-sample history is `RECENT_HISTORY_START` (2005-01-01) to
the experiment date, split 80/20 (`split_panel_holdout`'s default `holdout_fraction=0.2`) — roughly
**17.4 years** at the time these experiments ran. The best-measured instance of this family missed
MinTRL by on the order of **one tenth of a year**, not an order of magnitude.

## Why the panel is capped at 17.4 years when more real history exists

`RECENT_HISTORY_START = 2005-01-01` is a deliberate, documented choice
(`app/research/lab/history.py`): "the cross-sectional hunt... whose panel is bounded by its newest
member, so older bars per symbol buy it nothing." That reasoning is correct for the general case —
but it was checked against the *specific* 51-symbol universe behind these 11 experiments, not
assumed. Live yfinance queries (this session) found:

- **37 of the 51 symbols have continuous price history back to at least 1990.**
- **The other 14** (`NVDA, GOOGL, AMZN, META, TSLA, CRM, QCOM, AVGO, V, MA, GS, MS, ABBV, NFLX`)
  do not — they are the ones forcing the panel's common start to 2005, under exactly the
  "bounded by its newest member" logic the constant's own comment describes.

So the 2005 floor is working as designed for the universe as currently assembled — but the
universe was never specifically chosen to maximize track record for the family that turns out to
need it most. `RECENT_HISTORY_START` is shared by several other consumers (the paper book, broker,
cross-sectional forward scoring) and must not be changed globally. A universe assembled
specifically for long-history cross-sectional ranking is a separate, additive lever — see ADR-414.

## What this finding does NOT claim

- It does **not** claim `xs_quality` has a real, tradeable edge. DSR is deflated for a specific,
  stated reason (the lifetime-trial-count selection penalty), and that penalty exists precisely to
  prevent exactly the kind of overclaim this caveat is warning against. An 11/11 selection record
  is evidence the signal is the *least noisy* thing tried in this family so far — not evidence it
  is profitable net of costs and selection bias.
- It does **not** claim extending history will close the gap. 17.5 years was the SMALLEST required
  figure among the 11; several rows required 28–32 years, which no plausible history extension
  within this universe reaches. Extending history is worth trying because it is cheap, uses real
  already-available data, and is strictly evidence-increasing — not because success is assured.
- It does **not** weaken, bypass, or recommend weakening DSR, PBO, or MinTRL. The fix proposed in
  ADR-414 changes which data the search sees, not how the gate judges what it finds.

## Next step

ADR-414 proposes a long-history cross-sectional universe (symbols independently verified to have
1990+ price data) specifically for the quality/value family. ADR-415 (same session) corrects
ADR-414's mechanism — the universe file alone does not extend fetched history; `scripts/
cross_sectional_hunt.py` fetches every symbol from the hardcoded `RECENT_HISTORY_START` regardless
of universe. A first dispatch using only the new universe (run `42170667294`) proved this directly:
`xs_quality` won again (12/12) but the panel's start date was still `2005-01-01`, and its weaker
result (Sharpe 0.56 vs. the 0.96 peak) is not evidence against the history-extension hypothesis —
the panel never actually got longer, so that run did not test it. ADR-415 adds the missing
`HISTORY_START` override; the correctly-configured dispatch (`history_start=1990-01-01`) is queued
immediately after it, and its result will be added here as a dated addendum, whichever way it
comes out.

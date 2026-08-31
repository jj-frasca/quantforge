# ADR-072: Read the drift-controlled row two-sided

- **Status**: Accepted
- **Date**: 2026-08-31
- **Deciders**: Autonomous session #15 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-068 (excess over buy-and-hold), ADR-064 (matched-history null comparison)
- **Relates to**: ADR-038 (the one-sided criterion), ADR-051/067 (report what was measured)

## Context

ADR-068 built the `walk-forward excess` row and could not read it: every artifact on disk predated
the paired benchmark, so the row printed `NOT MEASURED`. The daily discovery has since re-searched
enough of the pool, and **on 2026-08-31 the row measured for the first time**:

| side | n | median | mean | p5 | p25 | p75 | p95 | share < 0 |
|---|---|---|---|---|---|---|---|---|
| **real, matched cohort** (77 experiments, 66 symbols, 7,345 bars) | 77 | **−0.125** | −0.186 | −0.549 | −0.308 | −0.018 | +0.021 | **75.3%** |
| `bootstrap:SPY` null, 7,400 bars | 200 | −0.006 | −0.028 | −0.233 | −0.037 | +0.000 | +0.096 | 55.5% |
| `iid_normal` null, 7,400 bars | 200 | +0.000 | +0.012 | −0.251 | −0.035 | +0.057 | +0.325 | 49.5% |

Both sides carry search fingerprint `3f36fda2…`; the real cohort is the ADR-063 long-history one
(6,686–8,112 bars), matched to the 7,400-bar nulls under ADR-064's ±10% tolerance.

**What the search adds out-of-sample, over holding the same series across the same windows, is
−0.125 Sharpe on real symbols and ≈0 on data with no edge by construction.** The real median sits
at the **11.5th** percentile of the bootstrap null's excess distribution and the **14.0th** of the
iid one. This is the first time the project has measured what its search contributes with drift
taken out of both sides, and the answer is that on real data it contributes less than nothing.

The reporting rule cannot say that. `real_exceeds_null_p95` is one-sided, so the row prints
*"does not separate (real median <= null p95)"* — the same sentence it would print for a real median
of +0.09. On the **raw** rows one-sidedness is right and deliberate: ADR-068 showed those two sides
are denominated in different drifts, so a real median below a null's says only that the median pool
symbol drifted less than SPY. The **excess** row removed exactly that. Both sides are differenced
against holding their own series over the same windows, zero means the same thing on both, and a
departure below the null band is therefore as interpretable as one above.

## Decision

The centered statistic is read against a two-sided null band.

1. `NullComparison` gains `null_p5` — the lower edge of the null's own distribution, reported
   beside `null_p95` in the CLI report, the `/api/v1/null-comparison` payload and the dashboard
   panel.
2. `NullComparison` gains `real_below_null_p5`. It is **False by construction on the raw rows**:
   there the two sides carry different drifts, so a low real median is a fact about drift, not
   about the search, and ADR-038's stated criterion stays one-sided and unchanged.
3. The verdict for a two-sided row is `SEPARATES` above the band, `SEPARATES BELOW` under it, and
   `does not separate` inside it. Renderers print the backend's verdict; none re-derives it.
4. **No threshold, gate, fingerprint or generated artifact changes.** This ADR changes what the
   report can express, not what anything is judged by.

**On today's numbers the verdict does not flip.** −0.125 is above the bootstrap null's p5 of −0.233
and the iid null's of −0.251, so the row still reads `does not separate` — now for a reason a reader
can see, against a band whose lower edge is on the page.

## The open question this raises, deliberately not decided here

The comparison is between a **median of 77** and a band over **individual null draws**. Those are
not the same quantity, and the mismatch makes the test enormously insensitive: the sampling SE of a
median of 77 draws from the bootstrap null's excess is ≈1.253 × 0.112 / √77 ≈ **0.016**, against
which −0.125 sits about **7 SE** below the null median. A test scaled to the statistic actually
being compared would call this a separation; the one on the page does not.

That is not a change to make tonight, and ADR-070's meta-lesson is why: **the standard error is
stated before the threshold, and a criterion is never re-scaled after seeing the number it would
act on.** It is also not obviously right — the 77 excesses are not independent draws. They come
from 66 symbols over one overlapping calendar window, and the finalist is `fifty_two_week_high` in
30 of 77, so the effective sample is smaller than 77 by an unknown factor and a symbol-clustered
or block bootstrap is the honest way to size it.

**A future ADR should state a cluster-aware criterion in advance, then apply it once.** The band on
the page stays the conservative one until then.

## Alternatives considered

1. **Make the raw rows two-sided too.** Rejected: ADR-068 measured that the raw statistic's level
   *is* the generator's drift, so its lower tail has no interpretation. A verdict that fires on it
   would report drift differences as findings.
2. **Report the real median's percentile rank in the null instead of `p5`.** More informative per
   character, but it is a derived number with no matching column on the null side, and the p5/p95
   pair keeps the row readable as one band. The percentile is recorded in this ADR where the
   argument needs it.
3. **Re-scale the band to the sampling distribution of a median at the real side's n.** The right
   test, and the reason for the section above — but stating it after seeing the number it would
   act on is precisely the failure ADR-070 recorded twice.
4. **Say nothing and wait for more data.** Rejected: the row is measured now and reads as neutral
   when it is not. `NOT MEASURED` was honest; "does not separate" with no lower edge on the page is
   not.

## Consequences

- The project can state, for the first time, what its search adds out-of-sample on real data with
  drift controlled: **−0.125 Sharpe, negative in three of four experiments.** That is a finding
  about the search, not about the market, and it is the strongest evidence the gate has produced
  that the in-sample argmax is fitting structure that does not persist.
- The dashboard and the CLI gain a `Null p5` column; consumers of `/api/v1/null-comparison` see two
  new fields. Nothing that was published becomes wrong.
- The one-sided reading of the raw rows survives untouched, so ADR-038/064's verdicts are unchanged.

## Reversal

Drop `null_p5` / `real_below_null_p5` and the `SEPARATES BELOW` branch. That restores a report which
prints the same sentence for a search that adds nothing and a search that subtracts.

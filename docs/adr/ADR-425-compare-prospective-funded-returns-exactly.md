# ADR-425: Compare the prospective funded screen on exact canonical prices

- **Status:** Accepted — prepublication ADR424 correction
- **Date:** 2026-11-07
- **Deciders:** Codex W45 session10 under standing autonomy
- **Extends:** ADR424; preserves ADR418 economic protocol and ADR417 account
- **Finding:** FINDING351 prepublication exact-tie screen

## Evidence and independent review before implementation

Independent research and data reviews both reproduce an exact positive-return
tie that falsely passes ADR424's initial float screen. Identical canonical prices
100 to101 for all83 selected/412 eligible/SPY give native funded_hold returns
0.007982017982018697,0.00798201798201248,0.00798201798201803. Two tiny positive
float contrasts plus positive cash excess pass all(value>0), although all three
exact net returns are799/100100 and the benchmark contrasts are zero. The initial
35 passing tests missed this case. No market incidence or actual outcome exists.
Both independent pre-adoption reviews approve the narrow correction below before
code. Retain their blocked initial reviews and actual targeted RED chronology.

## Decision and mathematical identity

Keep the original pinned funded_hold source, all its native companion account
reports, fees, turnover, drawdown and equity outputs unchanged. For the strict
economic screen only, use exact Fraction arithmetic from original canonical
PriceBar.close Decimal entry/exit operands, BEFORE float panel projection:

    gross_relative_leg = mean(Fraction(exit_i) / Fraction(entry_i))
    net_return_leg = gross_relative_leg * (999/1001) - 1

This is exactly the original equal-dollar fixed-unit cash account with one unit
capital and c=1/1000 each side: units_i=1/[k*(1+c)*entry_i], followed by liquidation
at(1-c). Do not divide Decimals first, rationalize a rounded float or average
already rounded ratios. Require complete source/DQ/calendar evidence before any
economic result, as424 already requires. No intermediate/subset economic output.

Subtract exact net returns for selected versus eligible EW and SPY; cash return
is zero. screen_passed is true ONLY when all three exact contrasts are strictly
positive. Exact ties fail. No epsilon, altered cost, threshold relaxation or
minimum effect size is introduced. Preserve tiny true positive/negative signs.

Retain exact net-return and net-excess rational strings plus a versioned method
and basis disclosure. Existing net_excess display values become float projections
of the exact contrasts; they are not necessarily subtraction of the native
companion report scalars. Display rounding to zero must never decide the boolean;
nonfinite projections refuse rather than clip. Native account reports remain
binary64 companions to the same intended account, not exact canonical arithmetic.
This does not certify vendor prices, fills or the economic adequacy of assumed
costs. No portfolio selection, dates, source policy, study root/window, trial
accounting, gate or other frozen cohort changes. No new economic experiment.

## TDD, acceptance and independent verification

First add an actual full413-series/64-close identical100->101 positive-tie test
and observe RED before source change. Include a false-positive control and strict
true positive/negative/tie contrasts, tiny sign-preservation cases and financial
Fraction properties. Preserve all existing35 tests and exact native account
outputs. Independently recompute means/costs/contrasts from retained canonical
source rows. The complete offline conformance report must include this exact tie
alongside flat FAIL, deliberately dominant selected PASS and source failure.
All are labelled synthetic and improve no alpha evidence.

Require fresh independent final research/data review of source, exact oracles and
retained artifacts, protected-file equality, foreground full gates and exact CI
before releasing the integrated424/425 unit. The initial pre-fix three parent
synthetic cases remain historical receipts, never final implementation evidence.

## Alternatives and reversal

An epsilon would change the strict economic hurdle and conceal tiny true effects;
it is rejected. Modifying pinned funded_hold would change historical companion
reports and source policy; unnecessary. Leaving the false screen is unacceptable.
Reversing this exact comparison requires a separate evidence-backed decision;
preserve this finding and never silently restore the known tie false positive.

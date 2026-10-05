# FINDING-109: Backtest capital curves can be nonfinite

- **Date:** 2026-10-05
- **Severity:** High — finite performance metrics can accompany undefined wealth evidence
- **Status:** Resolved by ADR-177

## Evidence

`BacktestEngine` checks only sign for capital and cost. With prices `[100, 110]`, full long
signals and zero costs, NaN initial capital produces `[NaN, NaN]` equity and infinite initial
capital produces `[inf, inf]`. Both return a finite +10% total-return metric because metrics
are fitted to net returns independently of the scaled curve. Even maximum finite initial
capital yields `[max_float, inf]` on this same valid +10% path. Conversely, the smallest positive
capital and 90% initial turnover cost round the positive remaining wealth to zero.

## Correction and limits

ADR-177 requires finite constructor capital/cost and checks every computed capital-scaled equity
value is finite and positive before returning a result. It declines unrepresentable observations;
it does not cap capital/costs or floor wealth. Ordinary accepted calculations, empty histories,
zero costs, and extreme but representable flat wealth remain supported. This is a synthetic direct
boundary reproduction, not a claim about any generated experiment or observed broker insolvency.
The engine's positive normalized research wealth is separate from the paper account ledger's
legitimate nonpositive account observations (ADR-169). No data or threshold changes.

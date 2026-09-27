# FINDING-070: Forward decisions bypass quality lineage

- **Severity:** High — paper scoring, lifecycle exits, and broker targets can consume vendor
  evidence that the mandatory quality gate would reject
- **Status:** Resolved by ADR-139
- **Date:** 2026-09-27
- **Affects:** single-name forward testing, managed paper lifecycle, Alpaca paper target sizing

## Finding

ADR-137 makes every new single-name research claim consume a quality-checked `ResearchDataset`, but
the production forward paths still call `fetch_price_bars` and immediately convert the returned bars
to a DataFrame. `scripts/paper.py`, daily pool consolidation, and `scripts/paper_broker.py` therefore
score or trade a frozen strategy without running `DataQualityEngine` over the exact fresh evidence.

Normalization alone does not enforce ADR-006's series-level symbol, source, calendar, request-range,
or minimum-data checks. A successfully normalized but failed report can change a lifecycle verdict
or the latest signal used to size a paper order. The resulting `ForwardScore` persists only derived
numbers, so the durable book cannot identify which quality report, adapter version, half-open range,
or executed revision supported the decision.

## Required correction

Make every production single-name forward provider return a quality-checked `ResearchDataset` and
make the pure portfolio/broker orchestration reject plain frames. Persist a frozen evidence record
beside each new forward score, binding the complete passed report to its source, adapter version,
requested range, and executed revision. Legacy scores remain readable with absent evidence rather
than receiving inferred lineage. A fetch or quality failure must leave a managed position unchanged
and must never produce a paper target.

Cross-sectional forward testing has a separate panel-identity problem and is intentionally outside
this finding.

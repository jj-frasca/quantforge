# FINDING-101: Paper benchmark can omit inception movement

- **Date:** 2026-10-04
- **Severity:** High — forward account alpha can compare different price windows
- **Status:** Resolved by ADR-170

## Evidence

`scripts/paper_broker.py` fetches SPY from `history[0].timestamp` and divides the last returned close
by the first. Under the documented half-open adapter contract, an evening inception excludes the
same day's midnight-labelled daily bar, even though that day's regular close was already available.
Synthetic daily closes 100, 110, 121 therefore give 10% instead of the completed-close proxy's 21%.
The first recorded account snapshot is after the New York regular close. This is a structural
offline reproduction, not proof of a particular live Yahoo response or a historical error magnitude.

The same unqualified ratio can use a current forming daily bar during an intraday manual run.
Midnight labels establish session identity, not close availability. Ignoring missing endpoint dates
can also silently substitute stale prices.

Two additional RED regressions show finite positive prices can overflow the derived float ratio
to infinity or round a tiny positive ratio to a false complete loss (-100%). These are declined as
unrepresentable evidence so a benchmark cannot make an otherwise valid account snapshot fail.

## Correction and limits

ADR-170 specifies checked acquisition with a bounded pre-inception lookback and exact expected
completed-close dates. Ambiguous intraday/calendar/quality observations remain unmeasured. Daily
close attribution remains a reporting proxy because after-hours account marks can differ. Historical
alpha is preserved; this fix changes only prospective measurement and contacts no broker in tests.

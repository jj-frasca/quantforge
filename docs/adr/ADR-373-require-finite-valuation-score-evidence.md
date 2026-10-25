# ADR-373: Require finite valuation-score evidence at construction

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Codex autonomous session34, ISO2026-W43
- **Resolves:** FINDING-316
- **Extends:** ADR-022/023/124/147/155

## Context

Ordinary UndervaluationScore validation admits nonfinite financial fields, which
can pass a finite value pre-screen and serialize as missingness. Extreme finite
synthetic canonical inputs also reach this state through the actual default
producer. F315/ADR372 concern config minima; ADR147 deliberately left shared
nested model classes unchanged. No actual company, graduate or trading effect is
established. Existing generated valuation leaves inspected are finite or null.

## Options Considered

1. **Require finite numeric fields on the shared valuation model.**
   - Pro: direct construction, JSON and final producer output share one refusal;
     native arithmetic and all finite evidence remain unchanged.
   - Con: new refusals can reduce record-first hunt availability and abort a sweep
     shard; previously serialized nulls remain unrecoverable.
2. **Guard only screen_value or the producer's composite field.**
   - Pro: covers a demonstrated consumer or output with a local guard.
   - Con: nonfinite auxiliary evidence can still be published or serialized away,
     and separate producer/direct-model paths would disagree.
3. **Recover overflow or convert it to absent components.**
   - Pro: may preserve more extreme-input availability.
   - Con: changes numerical/missingness methodology without an independent policy
     or precision proof; can turn invalid evidence into keep_unscored permission.
4. **Add score bounds, deep freezing and unchecked-copy reconstruction too.**
   - Pro: establishes broader model/consumer contracts.
   - Con: independent behavior changes need separate evidence and compatibility
     decisions; they are unnecessary for this constructor defect.

## Decision

Add only `allow_inf_nan=False` to UndervaluationScore's existing ConfigDict.
Preserve frozen=True, fields, nullable absence, finite values and coercions,
mutable flag-list behavior, JSON shape, producer/DCF/screen arithmetic and defaults.
ValidationError propagates through current callers; do not add recovery or None
fallbacks. No threshold, calibration identity, generated record or workflow changes.

## Consequences

New validated evidence and producer returns refuse nonfinite numeric fields.
Record-first hunt errors skip that symbol even with screening off. Earlier value
provider price acquisition may already occur; only downstream hunt acquisition
and search are skipped. A sweep scorer refusal can fail its shard before output;
no new per-record catch or partial-success policy is introduced. Existing instances
and unchecked model copies remain outside this construction boundary.

Write failing constructor/JSON, actual producer and synthetic provider/universe
tests before source changes. Use Hypothesis for finite numeric round trips and
retain nullable controls. Replay the frozen ordinary/generated payloads, source
hashes and exact whole AST except the single keyword; obtain final research/data
reviews and run foreground make check-all before individual push and exact CI.
Removing that keyword reverses this decision and reopens FINDING-316.

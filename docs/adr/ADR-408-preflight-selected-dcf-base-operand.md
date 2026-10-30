# ADR-408: Preflight the selected DCF base operand

- **Status:** Accepted
- **Date:** 2026-10-30
- **Deciders:** Codex autonomous session21, ISO2026-W44
- **Resolves:** FINDING-343 within selected latest-base consumption
- **Extends:** ADR-022/373/406/407

## Context

A nonfinite latest FCF or selected net-income proxy can become an ordinary
unsuccessful DCF and accepted composite/record, erasing invalidity. Growth checks
come later and output validation cannot see the dropped raw base. Parent and
independent synthetic witnesses confirm the gap; no production effect is known.

## Options considered

1. **Preflight the selected present base (chosen).** Local and contextual before
   comparison/erasure, but newly refuses formerly accepted malformed inputs.
2. **Validate IntrinsicValueResult numeric fields globally.** Covers other direct
   output invalidity but broadens model/derived-arithmetic policy and diagnostics.
3. **Validate all raw history globally.** Broader coverage but changes inactive
   inputs and other consumers without a scoped justification here.
4. **Treat invalid base as missing or try another proxy.** Keeps availability but
   hides present invalid evidence and changes the economic input selection.

## Decision

After the existing base-is-None return and before base<=0, require math.isfinite
on the selected base. Raise plain ValueError naming free_cash_flow or net_income
according to existing is_proxy, latest fiscal year and DCF base. No new selection
or model policy: None still selects proxy or returns missingness; present FCF
never switches to proxy on invalidity. Keep finite nonpositive returns and all
native arithmetic/flags, growth rules, shares guard, assumptions and schemas.
Do not inspect inactive lower-priority fields or add catch/recovery behavior.

## Consequences, verification and reversal

This deliberately supersedes ADR-406/407's preservation of *nonfinite* selected
base early returns. Selected-base refusal precedes shares, chronology and growth;
earlier multiple/quality errors still precede DCF in their callers. Finite and
missing base behavior stays; historical attempted growth validity stays. Provider
scoring remains outside acquisition fallback: hunts record errors before search,
while a sweep can fail its shard before output. No new partial-success policy.
No thresholds, v14, fingerprints, generated files, frozen cohorts or historical
reconstruction change. Derived precision and source/PIT truth remain separate.

Write failing direct/composite/single-row-record cases first, covering both
selected fields, all nonfinite values and erased paths. Explicitly update old
malformed-base expectations to this new named refusal without dropping direct
estimator or earlier quality coverage. Preserve finite/None and inactive inputs;
use Hypothesis for the independent perpetuity oracle. Replay 300 frozen complete
ordinary outcomes, obtain independent final review, run foreground make check-all
and verify exact CI after individual publication. Remove only this local guard
to reverse; then restore superseded malformed-base expectations and reopen F343.

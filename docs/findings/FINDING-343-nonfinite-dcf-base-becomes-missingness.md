# FINDING-343: Nonfinite selected DCF base becomes ordinary missingness

- **Date:** 2026-10-30
- **Status:** Confirmed; bounded correction specified by ADR-408
- **Producing revision:** e611d895

Ordinary validated single-row history with revenue=0, EPS absent and selected
FCF=-infinity returns a normal nonpositive-base DCF result. With NaN or positive
infinity selected base and missing/nonpositive shares, DCF instead returns its
ordinary unavailable-shares result. Raw fcf_base remains nonfinite in the direct
result but is absent from UndervaluationScore. Thus composite validation and
compute_fundamental_record both accept finite/null evidence with the invalid base
erased. Net income selected as FCF proxy has the same behavior. Independent ten
witnesses and parent eighteen cases reproduce it without unchecked construction.
The accepted composite score is None; no favorable score, actual vendor incidence,
admission, graduate, historical repair or trading effect is established.

ADR-406 validates attempted growth series only after early base/shares returns.
ADR-407 guards shares after base returns. ADR-373 checks composite output, which
does not retain the raw base. None covers this earlier selected operand. A final
IntrinsicValueResult finiteness rule would broaden an independent model/output
policy; a local selected-base preflight gives field/year context before erasure.

ADR-408 requires the present selected base finite before its nonpositive test.
It intentionally replaces malformed-base early returns and makes selected-base
refusal precede shares, chronology and growth consumption. Earlier multiples and
quality refusals keep their caller precedence. None remains absent; finite zero,
negative and signed-zero bases retain flagged results. Invalid present FCF cannot
fall back to net income; valid FCF leaves inactive net income uninspected.
Historical growth-series policy, native finite arithmetic, schemas, assumptions
and caller exception handling stay. Hunts record per-symbol errors before search;
sweep scoring can fail a shard before output. No new catch or substitution policy,
threshold, fingerprint, v14, generated-data or frozen-cohort changes are adopted.

Before source changes, the 132 new cases gave 120 failures / 12 passing controls.
After explicit pre-source updates to old malformed-base expectations, the expanded
suite gave 141 failures / 161 passing controls. No harness or expectation defect
was found in these receipts. The focused post-change suite passed 394 tests;
independent review approved with 313 passing tests, exact replay of 300 ordinary
full outcomes and whole-module AST exact outside the five-line guard. Existing
case counts and direct growth-estimator coverage remain; a Hypothesis perpetuity
oracle and finite/None/precedence controls are included. Full foreground gate,
safe publication and exact CI receipts are tracked in the ignored session ledger;
no pending verification is claimed completed here.
Derived arithmetic precision, physical periods/PIT, raw vendor authenticity and
unchecked configuration remain separate limitations.

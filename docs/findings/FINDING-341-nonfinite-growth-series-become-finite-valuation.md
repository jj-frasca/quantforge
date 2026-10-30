# FINDING-341: Nonfinite growth-series inputs become finite valuation

- **Date:** 2026-10-29, Codex autonomous session20 (ISO2026-W44)
- **Status:** Corrected within attempted growth-series raw-input consumption under ADR-406
- **Severity:** Medium — invalid historical input can yield accepted finite valuation
- **Producing revision:** `6936b6fd`
- **Affected:** `estimate_growth`, DCF and valuation/record consumers

## Evidence

A synthetic two-year history has FCF positive infinity then 120, with finite net
income 1, revenue 100, shares 10 and current price 100. The estimator returns growth -1;
the DCF clamps it to 0 and returns 147.32053821460278 per share. Valuation reports
finite score 0.32120801884168143 and FundamentalRecord accepts it. Finite first
FCF 100 instead gives native growth 0.19999999999999996, clamped 0.12, and DCF
242.8143427580083. These figures identify the executed synthetic paths, not a
claim about the economic value of malformed input. Negative-infinite first FCF
instead silently falls through to finite net-income growth. NaN may reach the
existing final nonfinite-output refusal, but that does not cover the finite cases.

Parent and independent research reproduce these outcomes. Additional controls
show an invalid interior FCF disappearing behind a valid endpoint calculation,
and None followed by NaN silently triggering fallback. Successful earlier FCF
currently ignores malformed lower-priority series. No actual vendor response,
company, incidence, screening change, graduate, trade or calibration effect is
established; no provider or real search was run.

F316/ADR-373 validates final numeric output; F325/ADR-382 validates assumptions;
F323/ADR-381 corrects fiscal-label annualization. None reconstructs raw growth
observations already erased to finite output. Piotroski does not inspect FCF.

## Bounded correction and limits

Preserve the fewer-than-two-row None return, then chronology validation and label
span. Visit FCF, net income and revenue in their existing order. For each attempted
series, require every present observation finite in original history order before
private _cagr eligibility, including interior values. First invalid value raises
plain ValueError naming field and fiscal year. None/zero/negative peers cannot
hide another invalid present observation in that attempted series. Once an earlier
series succeeds, lower-priority series remain unvalidated and ignored.

Keep _cagr's None/positive eligibility and native endpoint arithmetic unchanged.
DCF base/shares early returns may still bypass the estimator; no global Annual
schema or single-year DCF base-validity policy is introduced. Consumer errors
propagate through existing boundaries without new fallback, skip or recovery.
Availability deliberately tightens on attempted malformed series even when they
previously fell through. Finite-derived overflow/underflow/rounding, economic
ranges, source-period/PIT truth and historical lost inputs remain separate.
No threshold, search/gate identity, accounting-v14, generated record or frozen
cohort change is authorized.

## Verification

Before source changes, 1,206 complete direct/DCF/valuation/record outcomes, the
whole intrinsic-value module AST and three original test SHAs were frozen.
The original pre-code run had 97 failures and 9 passing controls with no
production diff; one failure was an incorrect test expectation about the preserved
DCF early return. Thus 96 original failures are valid new-refusal targets. The
first focused run had 239 passes and that one test failure; production stayed
unchanged. The corrected test explicitly asserts the DCF early None/flag and
separately checks direct estimator refusal; no test was removed or skipped.

A separate controlled run loads only the original HEAD estimator AST in memory,
without changing tracked production, and runs the corrected tests: 97 failures
(91 missing refusals, 6 expected named-error mismatches) and 9 passing controls.
This is corrected post-implementation regression evidence, not a new pre-code
claim. All 106 new tests then pass against the implementation; the parent focused
suite passes 240 synthetic tests. Independent research approves all six paths,
passes 205 tests and independently replays all 1,206 outcomes, the whole scoped
AST and three original test SHAs exactly. The session ledger tracks foreground
full-gate and exact publication CI verification and completion receipts. No
generated record or frozen evidence is rewritten.

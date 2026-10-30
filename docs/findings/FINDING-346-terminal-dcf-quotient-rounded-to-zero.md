# FINDING-346: Nonzero terminal DCF cash flow divides to zero

- **Status:** Corrected within finite-denominator terminal division (ADR-411); other precision remains open
- **Date:** 2026-10-30, Codex autonomous session24 (ISO2026-W44)
- **Severity:** Finite-input evidence loss under custom settings; incidence unmeasured
- **Related:** ADR-022/382/409/410; terminal discount loss remains separate

## Evidence

At 421f0bde, two synthetic annual rows with FCF1e-300, shares1, EPS1,
revenue100, net income1 and historical price10, plus admitted custom settings
discount1e300, terminal growth0, horizon0 and flat growth, produce terminal
numerator1e-300 and finite denominator1e300. The exact Fraction quotient of
these accepted native operands is positive and below half the least binary64
subnormal. Native terminal_value is zero. DCF returns zero; at current price1
the actual composite has score1, margin of safety None and flags[]. The actual
custom-settings value provider retains that claim and the default value screen
passes it. A negative terminal numerator also loses its magnitude/sign.

This is not confined to a zero accumulator or no-loop horizons. With base1e-210,
discount1e100, terminal growth nextafter(-1,0), flat growth and horizon1, native
period PV1e-310 remains nonzero while the terminal numerator's nonzero exact
quotient rounds to zero. At price1e-310 the existing composite is finite with
score2/3 and margin0. No affected default-settings record, vendor incidence,
historical result, false graduate or trading impact is established. These are
extreme constructed settings, not realistic corporate economics.

## Correction and limits

ADR-411 retains native multiplication and division, each once, and refuses a
nonzero terminal cash-flow numerator yielding zero terminal value with a finite
native denominator. It adds no precision recovery, fallback or economic bound.
True numerator zeros and nonzero quotients, including subnormals, remain native.
An earlier projection or terminal multiplication may already have lost evidence;
the separate final terminal discount may lose it later. Those losses, cancellation,
nonzero rounding and source/period/PIT truth remain outside this correction.
Unchecked infinite denominators retain their prior direct behavior and later
composite metadata refusal. Native earlier errors retain precedence; the new
terminal refusal can preempt later discount-power or metadata errors.

The two ADR-410 terminal-only no-loop loss controls are intentionally superseded
with explicit terminal refusal, retaining their original input cases. Ordinary
no-loop horizons and genuine zero terminal cash flow remain valid. Scorer errors
propagate outside provider acquisition recovery; hunts retain explicit per-symbol
errors before downstream price-frame acquisition/search, with screening on or off.
No new partial-output or workflow recovery policy is introduced. FundamentalRecord
does not accept these custom settings; no affected default record is inferred.
No threshold, fingerprint, v14, generated record or frozen cohort changes.

## Verification plan

Before source changes, freeze 1,146 complete unchanged direct/composite/record
outcomes, two separately identified changed target claims, the whole module AST
and seven original test hashes in /tmp/qf-w44-s24-terminal-baseline.{py,json}.
Use actual pre-code failing direct/composite/provider/hunt and exact Fraction /
Hypothesis cases, plus genuine zero, ordinary no-loop, subnormal, infinite-native-
denominator and error-order controls. Require independent research/data review,
foreground make check-all, individual fresh synchronization/publication and exact
master CI. Focused checks and bounded replay do not prove universal precision.
Actual receipts will be recorded here and in CODEX_RUNNING_STATE; no pending
verification is claimed as passed.

Actual pre-code RED collected 105 cases: 50 failures and 55 passing controls,
with production source unchanged. Of the 63 new cases, 48 failed as intended and
15 controls passed. Both retained ADR-410 no-loop loss cases failed their new
terminal-refusal expectation; its other 40 controls passed. The 50 targets were
36 direct/composite/provider missing refusals, 8 downstream-acquisition calls,
2 partial-accumulator refusals, 1 earlier-refusal/later-ZeroDivisionError case,
1 exact Hypothesis property and the 2 migrated cases. No collection or bad
expectation failures were included. After the narrow guard, all 151 focused
synthetic tests passed. Lint found one regex raw-string marker in the migrated
test, corrected after focused verification; lint and format checks then passed.

The 1,146 complete unchanged outcomes, scoped whole module AST and seven old
test hashes match exactly; two separately captured loss claims now explicitly
raise the terminal error. Research and data each independently reproduced 105
passing cases and the complete baseline comparison. Research also bound its
frozen AST/hashes to the producing Git revision; data independently restored the
old terminal expression in memory to reproduce both witnesses, then checked the
new refusal. Required full-gate/publication/CI receipts remain
in the session ledger; these focused checks do not claim unfinished gates green.

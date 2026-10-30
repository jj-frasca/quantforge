# FINDING-347: Nonzero terminal DCF value discounts to zero

- **Status:** Corrected within finite-factor final terminal discounting (ADR-412); other precision remains open
- **Date:** 2026-10-30, Codex autonomous session24 (ISO2026-W44)
- **Severity:** Finite-input evidence loss under custom settings; incidence unmeasured
- **Related:** ADR-022/409/410/411; separate final terminal discount operation

## Actual producer evidence

At c96aae6d, two synthetic years with FCF1e-300, EPS1, revenue100, net income1,
shares1 and history price10, plus admitted custom settings discount1e25,
terminal growth0, horizon2 and growth clamp fixed at -1e25, produce native period
PVs [-1e-300,+1e-300] with native sum0. The nonzero native terminal value
1.0000000000000003e-275 divides by finite native final discount factor
1.0000000000000003e50 to zero. Fraction(native terminal value)/Fraction(native
factor) is strictly positive below half the least binary64 subnormal. Direct
DCF returns0 and the actual composite/custom provider at current price1 yields
score1, absent margin of safety and flags[], passing the default value screen.
Negative terminal values also lose nonzero evidence.

A separate positive-period witness needs no cancellation: base1e-200, discount1e100,
terminal growth0, horizon1, flat growth produces period PV1e-300 and terminal value
1e-300 whose final discounted quotient becomes0. At price1e-300 the composite is
finite with score2/3 and margin0. The narrow refusal deliberately rejects even
loss too small to change the final rounded accumulated equity. Proof concerns
accepted native quotient operands, not exactness of all preceding arithmetic.
These are extreme constructed settings, not realistic economics, vendor or
population incidence, an affected default-settings record, historical graduate
or trading impact. FundamentalRecord does not accept these custom settings.

## Correction and limits

ADR-412 computes the existing native final terminal factor and quotient once,
refusing when nonzero terminal value produces zero discounted terminal value
with a finite factor. True zeros and nonzero subnormal quotients remain native.
No recovery, None substitution, setting bound or threshold is added. Existing
provider scoring remains outside acquisition recovery; hunts record per-symbol
failure before downstream frame acquisition/search, screening off or on.
No workflow catch or partial-output policy changes.

Earlier projection, numerator multiplication, subtraction, nonzero rounding and
accumulator cancellation remain separate. ADR-410 and411 refusals retain priority;
prior native power/division errors propagate. A new reached refusal may preempt
later share/metadata failures. Unchecked infinite-factor behavior stays outside
this finite-factor guard. No universal financial precision/source/PIT claim,
fingerprint, v14, generated record or frozen-cohort change follows.

ADR-410's two period-subnormal cases retain their exact original inputs but now
expect terminal-discount refusal, since their terminal terms were lost. Separate
terminal-growth=-1 controls retain the same signed period subnormals with genuine
zero terminal terms. Nonzero signed terminal subnormals and ordinary no-loop
horizons remain supported.

## Verification plan

Before source changes, freeze 1,192 complete unchanged outcomes, 24 separately
identified changed target claims, the whole module AST and eight original test
hashes (including ADR-411 tests) in
/tmp/qf-w44-s24-terminal-discount-baseline.{py,json}. Independent data prepared
this snapshot and verified the proposed candidate in memory; that is contract
review, not tracked pre-code TDD. Write permanent failing tests before source,
observe actual RED, then add the bounded guard. Obtain independent final reviews,
foreground make check-all, individual fresh sync/push and exact CI. Actual receipts
will follow here and in the local session ledger; pending checks are not green.

Actual pre-code RED collected 99 cases: 47 failures and 52 passing controls,
with production source unchanged. New tests supplied 45 refusal targets and 12
controls; both retained ADR-410 period-subnormal cases failed their new
terminal-discount expectation while the other 40 cases passed. The 47 targets
comprised 30 direct/composite/provider missing refusals, 12 downstream-acquisition
calls, 2 partial-accumulator refusals, 1 exact Hypothesis property and 2 migrated
old cases. There were no collection or incorrect-expectation failures. Draft-only
scratch collection had encountered a temp-root PermissionError before adoption;
that attempt is excluded from actual RED evidence.

After the narrow source patch, 208 focused synthetic tests pass, as do lint and
format checks. Research and data each independently pass 162 tests, reproduce
all 1,192 unchanged complete outcomes/scoped whole AST/eight original test hashes
and verify all 24 separately identified claims now refuse. Research binds the
frozen AST and hashes to the producing Git revision; data independently restores
the old expression in memory to reproduce both numerical composite witnesses
before confirming new refusal. Both approve the scope and retained original
inputs plus new genuine-zero-terminal signed subnormal controls. Required
foreground full-gate/publication/CI receipts remain in the session ledger; these
focused results do not claim unfinished release checks green.

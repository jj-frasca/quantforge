# ADR-398: Refuse nonfinite computed valuation multiples before ranking

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Codex autonomous session14, ISO2026-W44
- **Addresses:** FINDING-334
- **Extends:** ADR-022/023/124/373

## Context

Finite historical P/S operands can overflow in the native product before division.
Ranking discards that infinity into a finite percentile, so final ADR-373 output
validation cannot detect incorrect cheapness. Independent research/data reviews
confirm the actual multiple, valuation and record producers. No market incidence
or historical affected record is established.

## Options Considered

1. **Local _ranked guards before shortcuts (chosen).** Small change protects all
   computed current/history multiples without rearranging arithmetic or flags.
2. **Guard final MultiplesResult.** Historical inputs have already disappeared
   into finite ranks, so output validity alone cannot address the witness.
3. **Guard only percentile_rank.** Misses invalid current/thin-history values
   before _ranked's early returns. Generic primitive validity remains separate.
4. **Recover products or drop invalid entries.** Changes arithmetic/availability
   methodology and ranking population; neither is justified by this correction.

## Decision

At entry to _ranked, require a present current multiple finite, followed by each
computed selected historical multiple in existing array order. Guard before both
current-None and fewer-than-two-history shortcuts. Raise plain ValueError with
`current {label} must be finite for valuation multiples` or
`historical {label}[{ordinal}] must be finite for valuation multiples`.
Ordinal is zero-based among selected computed entries, not fiscal labels.

Keep native eligibility, current/history formulas, strict percentile comparisons,
counts, flags and thresholds unchanged. Existing P/E stage remains before P/S;
an earlier P/E refusal can preempt later P/S arithmetic. Other native exceptions
remain at their existing sites. Do not filter, recover, clamp, replace by None or
change shared schemas. Missing current/thin history with invalid computed entries
now explicitly refuses, an accepted availability restriction.

## Consequences and Verification

Refusal propagates through valuation and record/sweep consumers before DCF/output
construction; record quality still runs first. Provider scoring remains outside
acquisition fallback, and existing hunt per-symbol errors remain. No new catch,
skip or partial-output policy is added. Standalone percentile_rank, direct model
construction, raw invalid operands yielding finite results, finite rounding and
underflow, source/PIT truth and historical repair remain outside this slice.
No fingerprint, accounting-v14, generated evidence, cohort or threshold changes.

Before source changes freeze870 complete ordinary claims and module AST. Observe
actual failing synthetic tests for current/history P/E/P/S and consumer refusal,
including thin/absent-current history, named order and a fully mocked real sweep.
Use exact accepted-operand witnesses and native finite Hypothesis controls. Keep
missing/excluded/nonpositive/zero/tie controls. Replay full claims and whole AST
outside exact guards/import, obtain independent final research/data review, run
foreground make check-all, then publish individually and verify exact master CI.

Reversal removes only the guards and math import. Retain finding and ADR; never
rewrite generated or previously accepted evidence.

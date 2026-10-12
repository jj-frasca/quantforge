# ADR-266: Bound derived IC and validate original summary observations

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 3, ISO 2026-W42
- **Resolves:** FINDING-215
- **Extends:** ADR-035, ADR-264, ADR-265

## Context

summarize_ic([2,3]) publishes mean 2.5 as a correlation summary. Missing/nonfinite
or nonreal source cells can also become invalid summaries, while singleton inputs
bypass any observation checks. Strict source bounds alone would break valid callers:
perfect derived IC at some universe sizes rounds to 1.0000000000000002 despite
Cauchy-Schwarz proving the exact centered-rank correlation lies in [-1,1].

## Options Considered

1. Bound only finite derived correlations, then validate original summary cells.
   - Pro: closes invalid evidence while preserving legitimate endpoint roundoff;
     raw user observations are never repaired or hidden by conversion/shortcuts.
   - Con: changes finite derived IC endpoints by a rounding unit where they exceeded
     the mathematical range, and adds one summary validation pass.
2. Strictly bound summary inputs without correcting derived endpoints.
   - Pro: simple rejection rule.
   - Con: rejects valid perfect-rank outputs of the existing calculator.
3. Clip or tolerate out-of-range raw summary observations.
   - Pro: keeps computing for direct callers.
   - Con: manufactures valid coefficients from invalid evidence or permits a new
     arbitrary acceptance tolerance instead of enforcing the definition.

## Decision

After original defined-date selection, require the published derived IC values to
be finite, then project those finite values onto [-1,1]. Cauchy-Schwarz supplies
that exact range for the existing centered-rank formula. Do not turn nonfinite
arithmetic into an endpoint. Pairwise missingness/undefined-date dropping and all
rank/norm/correlation operations stay; only representational endpoint overshoot changes.

At summarize_ic entry validate every original supplied cell before float conversion
and the existing minimum-period shortcut: finite real scalar evidence within [-1,1].
Use the engine's existing native scalar finiteness helper (IC already depends on
engine), explicitly decline complex scalar encodings, compare original values to
integer endpoints without float narrowing, and normalize unsupported comparisons
to ValueError. Numeric strings are declined as unmeasured original numeric evidence;
there is no whole-Series dtype ban. Preserve valid bool, Fraction, Decimal, native
wide/nullable/ordinary observations, empty inputs and valid singleton None.

Keep the original to_numpy(dtype=float), mean/sample std/IR/t-stat/hit-rate formulas,
_MIN_STD=1e-12 and minimum-period count unchanged. Never clip, drop, fill or coerce
invalid raw observations to make them pass. No gate threshold, sample-floor, model-
leaf schema, summary precision-recovery or calendar policy is added.

## Consequences, identity and reversal

Finite direct derived IC endpoints may change by an ULP, including legitimate
production endpoints; disclose that correction rather than claiming all possible
finite outputs are unchanged. Independent canonical 16-generator/45-configuration
series and summary fixtures retain exact results. This diagnostic is not a selector,
gate or sizing input, and longitudinal calibration does not use it. Calibration
identity stays unchanged; historical generated records are not rewritten. ICSummary
model-leaf hardening and arbitrary summary arithmetic precision remain separate.

Observe RED for invalid native cells including beyond-endpoint Fraction/Decimal/wide
neighbors, singleton and cancelled-mean samples, and legitimate perfect-rank endpoints.
Verify original valid statistics/floor/short/empty behavior, native scalar comparisons,
strict caller state, adversarial Hypothesis invariants, canonical exact baselines and
independent review. Run foreground make check-all and individually deliver/watch CI.
Reversal restores original defined IC publication and removes summary source validation,
reopening FINDING-215 without changing the original statistic formulas.

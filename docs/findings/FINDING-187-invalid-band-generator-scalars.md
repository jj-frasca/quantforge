# FINDING-187: Band-generator arithmetic erases invalid original scalar provenance

- **Status:** Corrected by ADR-237
- **Date:** 2026-10-11
- **Scope:** mean_reverting_edge original model inputs after ADR-236
- **Decision:** ADR-237

## Evidence

With n_bars=20, seed=61, half_life=5, deviation_share=0.5, total_vol=0.012,
start_price=100 and default drift=0.0003, individually replacing half_life,
deviation_share, total_vol or start_price with True produces finite close prices
and finite gross filtered-mean reference Sharpe. Scores respectively are about
7.726885, 2.616066, 7.772088 and 1.031098. Original boolean evidence becomes
numeric derived rho/volatility or observations before the filter can validate it.
No corrupt committed artifact, new search or changed power count is inferred.

## Correction boundary

Validate original finite real nonboolean model scalars without replacing operands,
adding ranges or changing seeded draws. Keep existing n_bars/range precedence and
native comparisons. Derived generator arithmetic and unsupported mixed-type
recovery remain separate. FINDING-155 and FINDING-159 remain Open.

## Verification

The original pre-code run observed 75 failures/21 preserved cases, including an
overly narrow error-message matcher. After correcting that matcher, the published
pre-change generator function was reconstructed from git HEAD's AST in a separate
process: 63 failures/33 preserved cases. Production source was not reverted.
Boolean provenance failures were independently reproduced before implementation.
The initial affected run had 444 passes and 30 message-only assertion failures;
all 96 corrected new tests then passed in both parent and independent runs.

Independent review approved code/tests with 295 checks: 144 exact producer-field
comparisons, 144 exact gross/net latent/filtered reference scores across Python
and NumPy scalar types and source-law settings, and seven count/range/original
negative Fraction precedence checks. Removing the five calls restores the prior
generator AST. Final evidence/prose review approved. The first full gate had
4542 passes and one existing Hypothesis scheduling deadline flake (353.25ms then
4.47ms on replay, against unchanged 200ms deadline). Exact isolated replay passed.
A fresh full foreground make check-all with four workers passed 4543 backend and
363 frontend tests, lint, types and coverage. No deadline, assertion or validation
threshold was changed.

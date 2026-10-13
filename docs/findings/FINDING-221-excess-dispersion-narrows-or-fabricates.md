# FINDING-221: Excess dispersion narrows wider evidence or fabricates constants

- **Status:** Corrected (ADR-272)
- **Date:** 2026-10-12
- **Review:** Codex autonomous session 4, ISO 2026-W42
- **Decision:** ADR-272

## Finding and mechanism

Against zero benchmark, three native longdouble neighbors of .1 have exact
represented sample std 6.776263578034403e-21, but published pandas dispersion is
1.8117141909820796e-17. IR is 8.762147995199186e16 instead of
2.3426638712587207e20; tracking error is 2.876007117639097e-16 instead of
1.0756984947422253e-19. Neighbors of one and .5 reproduce the narrowing.
Installed pandas nanvar computes its mean/squared reduction with float64.
Repeated .1 excess may fabricate nonzero variance even for ordinary floats.

Repeated maximum uint64 excess retains zero dispersion in its original unsigned
representation, but encoding the same values as native wider floats produces
std 1.224744871391589 and IR 2.3909713014320703e20. Thus a separately reviewed
unsigned sign repair must follow this prerequisite rather than introduce a new
constant-dispersion regression. No historical market contamination is established.

The proposed wide mean-cancellation defect was dismissed: installed nanmean keeps
native floating dtype, and the exact Fraction/Decimal oracle agreed with the
published nonzero mean and IR for that fixture. No mean rewrite is authorized.

## Correction and limits

ADR-272 chooses exact excess constant detection across supported dtypes and native
anchored sample dispersion only for nonconstant genuine wider floats. Dispersion
stays native through existing IR and tracking formulas; final scalars are floats.
Ordinary nonconstant complete outputs, excess, mean, beta, alpha and drawdown
remain. Needed wider moment underflow refuses rather than fabricating zero IR.
This does not certify arbitrary cancellation, moments or float64 validation.
No gate thresholds, calibration identities or generated records change.

## Verification

Independent pre-code scratch: 224 exact represented Fraction/Decimal probes,
25 constant dtype controls, native dispersion outside float64 range, needed native
variance underflow refusal, and 80 unchanged complete nonconstant ordinary/nullable
comparisons. Session 6 reran the inherited tests against unchanged production:
24 genuine failures and 11 preserved controls, including the added constant
excess of nonconstant sources (the earlier 23/11 receipt preceded that test).
Only after RED and independent scope approval was the narrow helper/dispatch added.

All 222 affected benchmark/API tests pass; lint, format and strict mypy pass.
Final independent research-expert review approved 35 new tests, 48 exact represented
Fraction/Decimal IR/tracking-error probes, 7 constant dtype controls, 80 complete
ordinary/nullable comparisons against the current pre-code HEAD (including exact
excess dtype/name/index), and 20 strict-state wider/masked both-side overlap and
ownership probes. Removing only the helper/std dispatch restores the complete
baseline module AST. Native tiny dispersion retains nonzero IR when final float
tracking error rounds to zero; needed native underflow refuses under caller ignore.
The unchanged source float64 validation cast can still raise before this helper
under strict caller underflow; no whole-comparator strict-state claim is made.
Full foreground `make check-all PYTEST_WORKERS=4` passed: 5,699 backend tests,
97.72% coverage; 363 frontend tests, 97.63% statement coverage. All verification
completed before commit. No generated records, thresholds or calibration changed.

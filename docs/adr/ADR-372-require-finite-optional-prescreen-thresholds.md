# ADR-372: Require finite optional pre-screen thresholds

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Codex autonomous session34, ISO2026-W43
- **Resolves:** FINDING-315
- **Extends:** ADR-023 and ADR-029

## Context

An enabled value or quality pre-screen can admit a weak synthetic score when its
minimum is NaN, including through the CLI. Neither float comparison nor the
version hash refuses that malformed configuration. Independent direct, CLI and
mocked universe-admission witnesses confirm the defect. Defaults remain off; no
real hunt effect or false graduate is established.

## Options Considered

1. **Reject nonfinite threshold fields in the two validated config models.**
   - Pro: covers direct, JSON and CLI construction without changing screening math.
   - Con: previously accepted infinite overrides refuse, even when their comparison
     happened to be determinate. Existing finite overrides can express those policies.
2. **Handle only NaN in each CLI parser or screen function.**
   - Pro: addresses the demonstrated admission at a selected consumer boundary.
   - Con: leaves other construction paths or nonfinite configuration evidence open;
     duplicated guards can drift and enlarge the implementation.
3. **Restrict minima to [0,1] and validate other config fields simultaneously.**
   - Pro: defines a broader policy matching the nominal score range.
   - Con: rejects existing finite configurations without evidence for that policy;
     unrelated coercion and flag decisions do not belong in this correction.

## Decision

Add only `allow_inf_nan=False` to the existing ConfigDict for QualityGateConfig
and ValueGateConfig. Preserve frozen=True and every other declaration, method,
parser, comparison, default, flag and hash formula. Finite out-of-range values and
existing finite coercions remain supported. The default optional screens remain
off and their enabled minimum remains 0.5. No graduation predicate, threshold,
search accounting identity, producer, generated artifact or workflow changes.

## Consequences

Ordinary validated construction, JSON loading and CLI numeric overrides refuse
nonfinite thresholds before they can define a screen. ValidationError remains a
ValueError; invalid numeric tokens are not silently converted to symbols or a
different threshold. Unchecked model_copy/model_construct inputs and validity of
separate score models remain outside this constructor contract. No historical
config or generated record is rewritten, and no calibration is performed.

Write failing tests before source changes for both models, JSON and CLI inputs.
Use a Hypothesis finite-threshold round-trip invariant and preserve disabled
screens. Replay the frozen finite controls and whole-module ASTs, obtain final
research review and run foreground make check-all before individual publication.
Remove the two ConfigDict keywords to reverse, reopening FINDING-315.

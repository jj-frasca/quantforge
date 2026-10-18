# ADR-312: Qualify horizon reference reporting

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** Codex autonomous session 28, ISO 2026-W42
- **Relates to:** ADR-042, ADR-055, ADR-061, ADR-239, ADR-310, FINDING-159

## Context

The horizon console still calls a selected in-sample reference ratio an upper
bound and the specified historical filtered score the recoverable edge. A
refused filtered ratio is described as absence of anything to capture, even
though refusal also covers incomplete arrays or missing history. F159 documents
the historical log-mean/simple-return mismatch and startup covariance mismatch.
ADR-239 qualified comments/docstrings only; changing printed scientific claims
requires this separate reporting decision.

## Options considered

1. Qualify console claims while preserving every calculation and presence policy.
2. Wait for a corrected reference: leaves misleading output active.
3. Integrate ADR-310 and a corrected simple-return mode here: mixes reporting with
   a new methodology/attribution contract and is rejected for this slice.

## Decision

Describe latent gross/net and specified filtered net reference strategy scores,
selection-biased in-sample reference-relative ratios, and the existing generic
evidence/denominator refusal. State historical log-mean signs are scored on simple
returns, historical filter startup/posterior is uncertified, and these comparisons
do not establish cost-aware optimality, a sample maximum or absence of tradeable
edge. Identify historical driver conventions without certifying arbitrary supplied
score-array provenance. Describe supplied synthetic history rather than equating
it with every real hunt.

Change only human print strings, the horizon module's introductory explanation
and comments, and three PowerCalibration docstrings: oracle_sharpe_percentiles,
net_oracle_sharpe_percentiles and achievable_capture_ratio. Qualify the stationary
predictable-log-variance fraction without turning it into a strategy ceiling.
Preserve all branches, properties, numeric expressions/format specifiers, source,
scorer and measurement calls, parser/defaults and stored outputs. Shared percentile
docstrings describe stated references rather than labeling every process latent.
No schema, method, filter, threshold, artifact or cohort changes. F159 stays Open.

## Verification

Before print changes observe failing report cases built from small hand-constructed
PowerCalibration values: positive ratios, denominator refusal, incomplete evidence
and absent optional arrays. Verify scientific qualifications and preserved numeric
output. No generator, scorer, search or posterior is invoked. Compare source ASTs:
only approved docstrings and report string constants may differ; all numeric format
specifiers and executable scientific operations remain exact. Independent research
review, full foreground make check-all, individual publication and exact master CI
are required. Existing tests remain intact.

## Consequences and reversal

Console readers get appropriately limited reference comparisons; historical scores
keep their meanings. This is no empirical power result or production mathematical
correction. Revert this reporting-only commit to reverse it; doing so restores the
unsupported claims. A future corrected mode requires separate governance and exact
method/source-law attribution through producers and consumers.

# ADR-403: Disclose recorded graduate DCF settings

- **Status:** Accepted
- **Date:** 2026-10-29
- **Deciders:** Codex autonomous session16, ISO2026-W44
- **Partially addresses:** FINDING-325's known disclosure gap
- **Extends:** ADR-022/023/147/369/402

## Context and Options

ADR-402 retains actual settings in new backend valuations, but graduate API/UI
projections still expose only the scalar. Research, data and frontend reviews
approve disclosure without recomputation or inferred historical defaults.

1. **Graduate disclosure from the existing winning row (chosen).** Small read-only
   projection preserves identity and makes settings inspectable; other views and
   historical absent evidence remain incomplete.
2. **Expose whole valuations or complete replay inputs.** More context, but much
   broader API/UI and source/code attribution than the settings now retained.
3. **Look up a matching experiment again in the API.** Avoids a carrier field but
   duplicates winner selection and risks combining scalar and settings identities.
4. **Display assumed defaults for old scores.** Simple but invents attribution.

## Decision

During existing rank_experiments row construction, copy dcf_assumptions from
that same experiment's valuation into an INTERNAL default-None LeaderboardRow
field with exclude=True. Preserve every ranking key, first-tie behavior and
source graph. This carrier is transient Python transport, intentionally excluded
from leaderboard serialization and its public serialization schema; it is not a
new persisted artifact or public leaderboard field. Source experiments still
come from the existing validated stores; add no whole-graph rank validation.

GraduateRow adds optional None-omitted dcf_assumptions with a frozen strict
extra-forbidden finite view: four original floating settings and projection_years
as a canonical signed decimal string. Convert the admitted original integer
directly with str, never through float. This preserves integers admitted by the
existing ADR-402 serialization boundary, including beyond JS safe integers; it
does not remove Python's integer/string limits. Require canonical zero or signed
nonzero decimal digits, without plus, negative zero, leading zero, exponent,
whitespace or line terminators. Do not impose new financial bounds/order or
positive-horizon rules. No fetch, inference, rerun or gate calculation occurs.

The existing frontend Zod boundary accepts missing/null as unknown and validates
present complete finite settings and canonical horizon text without numeric
conversion. Malformed present evidence fails through the existing error state;
never substitute defaults or unknown. In the undervaluation cell retain the scalar
and add native collapsed details labelled Recorded DCF settings with five semantic
labels. Show recorded settings even when the scalar is null. Missing/null metadata
visibly reads DCF settings not recorded even when the scalar exists.

Format rates with Intl percent formatting on the original finite value, avoiding
an overflowing value*100. Render horizon text directly, including nonpositive
values, without treating bounds as realized growth. Scope wrapping and bounded
cell width for extreme percentages/long horizons; preserve keyboard/native
summary interaction and existing verdict/ranking/loading/empty/error behavior.
Explain that recorded settings alone do not reproduce or validate the score.

## Consequences and Verification

This discloses retained settings on the graduate view only; fundamental records,
other projections, pruned/legacy rows, source facts/PIT, pricing and producing
code remain separate. It does not establish that all knobs affected an
unsuccessful DCF or that settings determined graduation. No numerical score,
ranking, scientific estimator, threshold, fingerprint, v14, generated record or
frozen cohort changes. Old readers may discard new metadata.

Write contracts and tests before implementation; observe RED in both stacks.
Verify exact winner/tie binding, legacy omission, unchanged leaderboard JSON and
serialization schema, finite settings and exact signed horizon strings, actual
endpoint/store projection and source nonmutation. Frontend tests cover collapsed
interaction, scalar-null/present settings, unknowns, malformed data, extremes and
existing states. Preserve scalar/verdict assertions when accessible cell names
gain disclosure text. Freeze/replay ordinary payloads outside the addition.
Require independent reviews, foreground make check-all, individual safe push and
exact master CI. Reversal stops display/projection while retaining stored ADR-402
evidence; never rewrite historical data.

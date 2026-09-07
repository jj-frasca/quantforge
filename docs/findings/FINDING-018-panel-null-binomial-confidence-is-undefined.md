# FINDING-018: Panel-null binomial confidence is undefined

- **Severity:** High — the omitted confidence construction can change whether the fixed
  400-replicate experiment reports separated, not separated, or unresolved
- **Found:** 2026-09-06 by Codex implementation review of ADR-081
- **Status:** Resolved by ADR-082
- **Affected:** ADR-081 panel-null inference

## Finding

ADR-081 correctly freezes two tail counts and requires an exact binomial confidence interval for
each tail probability, but it does not specify the confidence level, whether the intervals are
one- or two-sided, or whether their coverage is simultaneous across the two reported tails. The
decision then defines its three-way resolution by whether those intervals lie above or below
0.025. Different conventional choices therefore produce different answers from the same immutable
400 panel replicates.

At `n = 400`, this is operational rather than cosmetic. Under a familywise 95% construction using
two 97.5% Clopper–Pearson intervals, a count of 3 has upper bound about 0.02414 and resolves below
0.025, while a count of 4 has upper bound about 0.02794 and remains unresolved. A less conservative
per-tail interval can move that boundary.

## Impact

Implementing the unspecified interval would silently spend researcher degrees of freedom after the
panel results exist. Because ADR-081 forbids extending or reinterpreting the experiment after seeing
the answer, the confidence construction must be frozen before any inference code, workflow, or
measurement is produced.

## Resolution

ADR-082 fixes a simultaneous familywise-95% construction: each tail count receives a two-sided
97.5% Clopper–Pearson interval (`alpha = 0.025`, split equally between its bounds). Bonferroni then
guarantees at least 95% joint coverage across the two reported tail-probability intervals. The
existing 0.025 tail threshold, 400-replicate count, plus-one p-value, and three-way resolution remain
unchanged.

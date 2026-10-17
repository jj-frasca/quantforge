# ADR-306: Isolate categorical axis definition buffers

- **Status:** Accepted
- **Date:** 2026-10-17
- **Deciders:** Codex autonomous session 25, ISO 2026-W42
- **Resolves:** FINDING-261
- **Extends:** ADR-165/302/304

## Context

Pandas deep copying isolates categorical codes but retains the categories' numeric
owner. Both public splitters therefore return independent prices while a public
search.index.categories NumPy owner can still mutate actual held-out/source labels.
Categorical column axes and categorical MultiIndex levels exhibit the same alias.
This is numeric label storage, within ADR-304's axis claim, rather than recursive
mutable object cells. Canonical datetime axes remain isolated. No production
occurrence, catalog use, false graduate or historical cohort effect is established.

Unused category/level metadata may include labels absent from a slice. Retaining
that metadata is normal pandas behavior and is not itself a held-out-price leak.
Removing it would alter the existing exact axis contract.

## Options considered

1. Recursively copy categorical definitions and MultiIndex levels through public
   pandas APIs while preserving exact axis metadata. Chosen.
2. Remove unused categories/levels or coerce to plain indexes. Changes dtypes,
   category order or identity rather than isolating existing evidence.
3. Restrict splitters to DatetimeIndex. Breaks ADR-302's ordered generic inputs.
4. Trust copy(deep=True), readonly views or copy.deepcopy. Pandas' category owner
   sharing remains; a readonly view can expose a writable public base.

## Decision

Extend only research.frames.copy_frame's axis recipe with a private typed helper.
For CategoricalIndex, construct Categorical.from_codes with independently copied
codes, recursively copied categories and the original ordered flag, then restore
the original index name. For MultiIndex, copy(deep=True) and replace every level
with its recursive axis copy through public set_levels. Use verify_integrity=False
for that exact-equal level replacement: this adds no code normalization or new
validation/refusal policy. Other axis families retain their original copy(deep=True).
Retain frame.copy(deep=True), numeric values/dtypes, dataset private alias and
descriptor behavior, split guards/geometry and every scoring function.

Preserve category/level values and order, codes including NA codes, unused metadata,
ordered flags, names and exact axis types. Do not recursively freeze mutable Python
objects inside cells/categories, attrs graphs, arbitrary extension internals or
hostile introspection. Bounded family checks are not a universal pandas ownership
proof. Extra category/level allocations are accepted; no method, threshold,
configuration hash, accounting-v14, generated record or frozen source changes.

## Verification and reversal

Observe actual category-owner sharing/mutation RED before code through copy_frame
and both public splitters. Cover row/column axes, source/search/holdout actor writes,
categorical date definitions, both categorical MultiIndex levels, codes, names,
unordered/NA compatibility and unused metadata. Compare exact original axes/frames;
keep numeric prices and canonical datetime/plain MultiIndex controls. Use Hypothesis
for category-owner mutation isolation and reconstruction, without shrinking existing
property domains. Independently review the source scope, compare the four frozen
standalone scientific payloads, run foreground make check-all and exact pushed CI.

Restore direct axis.copy(deep=True) calls and remove the helper to reverse, reopening
FINDING-261. Preserve the finding and all historical/generated evidence.

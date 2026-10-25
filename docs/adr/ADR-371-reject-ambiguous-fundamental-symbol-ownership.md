# ADR-371: Reject ambiguous company ownership at fundamental symbol projection

- **Status:** Accepted
- **Date:** 2026-10-25
- **Deciders:** Codex autonomous session32, ISO2026-W43
- **Resolves:** FINDING-312
- **Extends:** ADR-029/142/143/155

## Context

The CIK-keyed pool can legitimately retain different companies sharing a ticker
label. The current weekly file newly contains two PARA CIKs. score_maps selects
legs by input order and can combine scores from different companies; the quality
provider chooses by fiscal year instead. Neither heuristic identifies the current
security owner. Default universes inspected exclude PARA; no actual search or
trade effect is established. Generated records must remain untouched.

## Decision

Add ambiguous_fundamental_symbols in the record module: group records by
symbol.upper() and return keys with more than one distinct CIK. Case folding is
for collision/request membership only; preserve existing output-map key spelling.

score_maps checks this set before either optional-leg filter and raises ValueError
with sorted ambiguous names. Keep its existing dictionary comprehensions and
return shape on unambiguous inputs, including repeated records from the same CIK.
Do not choose an owner by year/score or convert ambiguity to ordinary missingness.

make_quality_provider captures the same ambiguity set at construction but refuses
only when its returned callable receives an ambiguous symbol. Preserve its existing
same-CIK newest-year/tie behavior and lookup case handling. This avoids failing
unrelated names or a screen-OFF run at provider creation, while preventing
keep_unscored from turning an ambiguous owner into technical-only permission.
The existing per-symbol ValueError handling records refusal before frame fetch
and search; the earlier single-name value-provider call is not reordered.

The cross-sectional driver loads the full pool, records each global leg's supplied
presence using score is not None, and projects records to its frozen resolved
requested-symbol set before score_maps. Requested ambiguity refuses before price
acquisition/search, even if that name might later fail fetching. An unrelated
ambiguous record outside the requested universe does not block the run. Pass an
empty dict when a globally supplied leg has zero requested coverage; use None
only when that leg was globally absent. Preserve family eligibility, allocation,
missingness and frozen-snapshot semantics rather than silently dropping a family.
Update the printed count label to identify requested fundamental scores.

No CIK-keyed merge, company ranking, row schema, provider source, price universe,
factor formula, gate threshold, longitudinal-v14 identity, generated record or
frozen snapshot changes. Existing supported unambiguous projections retain exact
scientific inputs. This guards current source projection, not historical owner
certification or arbitrary unchecked model copies.

## Alternatives and tradeoffs

- Pick the newest fiscal year or highest score: cannot identify current ownership;
  metadata anomalies and corporate transitions make these invented identity rules.
- Drop ambiguous symbols as missing scores: can fabricate coverage/family changes
  and permit a quality screen through keep_unscored.
- Reject the entire global pool eagerly: blocks healthy unrelated panels and
  even price-only hunts whose quality provider is never queried.
- Resolve ambiguity after price fetching: makes identity admission depend on
  eventual survivors and delays a refusal already available from source evidence.
- Rewrite/prune generated records or add vendor identity resolution: violates
  single-writer ownership or needs a separate source/provenance design.

## Verification and reversal

Write failing tests before implementation for reversed-owner order, complementary
legs, all-missing scores, case aliases, lazy per-symbol quality refusal and
requested-driver behavior. Hypothesis verifies cross-company composite refusal
under record order/score changes. Preserve same-CIK history, raw keys, zero scores,
None versus empty mappings, family eligibility and prior provider ordering.
Independent pre-adoption policy probes compare320 registry/snapshot cases and805
signals, including147 zero-requested-coverage cases. Capture/replay actual source
payloads and whole-AST scope; run independent research/data final reviews and
foreground make check-all before individual push and exact CI. Preserve input
hashes; no source fetch, real search or generated-data rewrite is required.

Remove the guards/helper and restore prior driver map construction to reverse,
reopening F312. Preserve original evidence and all generated/frozen files.

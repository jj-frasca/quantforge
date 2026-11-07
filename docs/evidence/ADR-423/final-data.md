# ADR-423 independent final data review

Verdict: **APPROVE** the frozen implementation and concrete source/result package
reviewed here. No remaining data-contract blocker. This is an independent
nonimplementing review. No product edits, HTTP requests, new source/return cohort,
credentials, generated-data writes or changed source interpretation occurred.
All review processes/imports have completed; the parent still owns the required
foreground full gate and publication CI.

## Independently executed verification

- Focused new suite: **48 passed in1.09s**. Log:
  `/tmp/qf-w45-s9-423-independent-data-tests.log`.
- Baseline replay: **22 complete default claims,4260 legacy records and1039
  protected hashes EXACT**. The1039 are the combined protected generated/source/
  old-test inventory, not1039 newly added tests. Log:
  `/tmp/qf-w45-s9-423-independent-data-baseline.log`.
- Original quality/record source snapshots match `git show a22fc109:<path>`
  byte-for-byte. Their stored AST snapshots also match when read with the project
  Python3.12. An initial system-Python3.11 AST check differed only because3.11
  omits3.12 type_params fields; it was not a source or financial mismatch.
- Independent AST normalization removes only declared new imports, optional
  evidence fields/validator/arguments/wiring, denominator aliases and their
  specified uses, plus documentation strings. Remaining quality and record AST
  is EXACT. Script: `/tmp/qf-w45-s9-423-independent-data-ast.py`.
- Independent source-row/Fraction oracle and full integrated-result replay:
  `/tmp/qf-w45-s9-423-independent-data-replay.py` and corresponding `.log` output.
  The complete portable `result.json` equals this independent execution, not
  merely its headline numbers. Manifest artifact/code/dependency hashes,
  compressed baseline raw equality and every verification-archive member hash
  match. No source method or financial value was changed for this verification.

## Source and actual result

The evaluator receives the original decompressed3,789,099-byte capture, SHA256
73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43,
with the retained official CompanyFacts URL and inherited observation completion
2026-10-30T07:28:44.145492+00:00. It hashes actual bytes before source selection;
this is no JSON reserialization standing in for the transport capture.

I independently matched all seven groups directly in those bytes: two literal
NetIncomeLoss/USD intervals and five Assets/USD groups at three physical dates.
Each actual group has one row. Form/FY/focus/filed labels, exact accessions,
absent Assets start, income start/end, physical continuity and comparative
value agreement hold. Known incomes94680000000/99803000000 and closing Assets
323888000000/351002000000/352755000000 match retained evidence. Every retained
actual group row equals the independently selected original row.

Exact consumed-operand ratios independently equal:

- Closing:47340/175501 ->99803/352755, improving.
- Beginning:11835/40486 ->99803/351002, declining.

The actual scorer produces defaultFscore8/trendTrue -> opt-inFscore7/trendFalse.
The other eight verdicts are unchanged. Actual quality changes from
0.6675842309900554 to0.6305471939530184 through the unchanged blend; GP/safety
are exact. Record F-score/quality equal actual scorer outputs, with value/combined
absent. Full supplied history and all original fields remain unchanged, hash
8e045a29c19c5a1baaa891c2635f8f9184e49da6daedca0901d8280fca7749bc.
The history/record retains original2025 accession0000320193-25-000079; separate
ROA evidence attributes2021/22. No revenue-derived period_end was repaired or
used to certify Assets dates.

## Contract conformance

Actual beginning denominators feed all three intended ROA/CFO ratios and their
existing zero-underflow/exact-predicate operand tuples. No final bit override,
point subtraction, shared-ratio rewrite or guard weakening exists. Explicit
evidence binds complete history and scalar projections before the short-history
shortcut; malformed, conflicting, missing, nonpositive or unrepresentable source
evidence refuses instead of generating a partial score.

The earlier review findings are resolved with retained actual RED controls:
exact group agreement precedes projection, canonical source order includes an
exact-spelling tie-break, and nonzero NI/Assets projecting to zero refuses.
Actual-byte source acceptance and specific refusal expectations were corrected.
The recorded initial permissive-test15FAIL14PASS is distinct from corrected
preimplementation29FAIL; subsequent targeted REDs cover projection/canonical
ordering and actual pool/shard JSON evidence preservation.

New strict evidence models are immutable and revalidate nested supplied claims.
Their bounded canonical date/time/list readers allow existing pool/shard JSON
roundtrips without changing old models. Quality/Record retain evidence omitted
whenNone. Producer evidence-plus-any-price refuses before scoring/valuation;
direct evidence-bearing Record refuses value/combined and binds available
issuer/symbol/latestFY. Whole-winner merge retains its chosen record's evidence;
a legacy incoming winner remains explicitly unknown. Default serialized claims
and existing numerical/error behavior remain exact in the frozen baseline.

## Interpretation and limits

This approves one known-exposed conditional denominator-basis implementation,
not new OOS return evidence, all-filer coverage, original-DEI/XBRL authentication,
complete Piotroski replication or historical PIT. Source observation is an
inherited capture claim, not first public availability; direct supplied evidence
models are attributed claims and cannot authenticate bytes by possessing a hash.
NetIncomeLoss numerator equivalence, other legacy periods, CFO mapping,
turnover/share/split basis and empirical effects remain unresolved. Alpha case
is **not improved**; financial gates remain NOT MEASURED. No prior selection or
trial count is reset, and ADR417/418/422 plus all frozen roots remain unchanged.

## Final documentation verification

Both exact README reproduction blocks were extracted and executed independently
without modification. Complete known-witness result/implementation identities
PASS; frozen-key checkpoint replay PASS for22 histories,4260 legacy records and
1039 protected paths. This second command correctly uses the checkpoint's frozen
keys rather than expanding its historical denominator after publication.

README and the final F324 append accurately state the actual FY2020 revenue
period_end/Assets date equality and qualify it as insufficient evidence of
annual income or balance identity. No claim that date inequality actually occurs
in the fixed witness remains. The480080-byte complete baseline is below the
unchanged500KiB hook; ADR423 registers no450KiB cap, and the distinct receipt
archive is not a split checkpoint. No source or result reinterpretation occurred.

All independent review commands have exited successfully; no imports, tests or
verification sessions remain running. Final source/result/documentation verdict:
APPROVE, subject to the parent's still-required full gate and exact publication CI.

# ADR-399: Retain supplied fundamental history citations

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Codex autonomous session14, ISO2026-W44
- **Partially addresses:** FINDING-335
- **Extends:** ADR-022/029/155

## Context

F335 establishes that FundamentalRecord drops the supplied history envelope.
Reporting is now qualified, but future records can preserve that attribution
without guessing historical citations or changing score/merge methodology.
Independent research/data reviews approve a nullable supplied-metadata boundary.
Installed and locked Pydantic2.14.1 supports omission of unknown optional fields.

## Options Considered

1. **Nullable frozen history_citation (chosen).** Retains supplied scalar metadata
   with explicit legacy unknown state and company binding; no source reconstruction.
2. **Full fact-level provenance, dates and producing code.** Potentially valuable,
   but unavailable from this boundary; requires upstream evidence and separate policy.
3. **Infer citations from company/year or fetch current filings.** Cannot recover
   historical attribution and would fabricate evidence. Rejected.
4. **Reporting only indefinitely.** Honest but needlessly discards supplied metadata
   in new records. Keep its qualifications while adding bounded retention.

## Decision

Add FundamentalHistoryCitation with seven required strict scalar fields: symbol,
cik, entity_name, form, accession_number, source_url, source. Use frozen=True,
revalidate_instances="always", extra="forbid", strict=True. Retain supplied values
without normalization, URL/nonempty requirements or invented economic validation.
FundamentalRecord.history_citation defaults None and omits None in Python/JSON
serialization through Field.exclude_if. Historical missing/explicit-null inputs
remain unknown and serialize without the field. Present citation symbol/CIK must
match the enclosing record, in a separate validator after existing combined-score
validation. Nested malformed unchecked copies revalidate; outer reconstruction
semantics remain unchanged.

compute_fundamental_record copies the actual supplied seven fields after existing
quality/valuation/combined computations. Include empty histories: the citation
identifies supplied input metadata, without asserting observations or an as-of date.
Empty numeric values, fiscal_year0 and flags remain unchanged. Invalid unchecked
metadata can now refuse after scoring; do not replace it with unknown attribution.
No fetch, inferred date, code revision or source-authenticity check is introduced.

Merge keeps its higher-fiscal-year/incoming-tie whole-record selection. The winner
carries its own citation; an incoming legacy tie may replace known attribution
with unknown. Never borrow a losing record's citation. Old writers may discard the
new field; additive reader compatibility does not certify old-writer preservation.

## Consequences, Verification and Reversal

This retains a supplied history-level envelope only. It does not certify fact
ownership/periods, source authenticity, availability/PIT, price provenance, code
revision or filing freshness. Valuation's separate default source label remains
unchanged. No score, flag, threshold, fingerprint, v14, generated-file migration,
provider or search/cohort change occurs. Strictness applies to new citation data,
not previously accepted legacy records without it.

Capture108 producer claims,108 legacy JSON claims,4 merge payloads, all4258 current
generated rows with raw SHA and module AST before implementation. Observe failing
tests before code for retention, strict metadata, immutability, binding, JSON,
empty history, error precedence and whole-winner merges; keep legacy omission
controls. Compare producer claims outside the explicit addition, legacy claims and
generated hashes exactly, and AST outside frozen declared additions/docstrings.
Require final independent reviews, foreground make check-all, individual safe
publication and exact master CI verification.

Reversal removes the field/model/validator/producer keyword and reopens retention
loss. Previously generated citations must not be edited or erased; old software
may ignore them. Preserve F335 and this decision.

# FINDING-095: Dataset evidence skips instance and timezone validation

- **Severity:** High — invalid acquisition provenance can reach direct forward consumers
- **Status:** Resolved by ADR-164
- **Date:** 2026-10-04
- **Affects:** ADR-137, ADR-139, ADR-140, and ADR-156

## Finding

`ResearchDatasetEvidence` accepts a requested interval with two naive timestamps. A mixed
naive/aware interval raises a raw comparison `TypeError` instead of a structured validation error.
Aware offsets retain multiple representations of the same acquisition instant.

More seriously, an unchecked `model_copy` of otherwise valid evidence can replace its quality
report with another unchecked copy whose `checked_at` is naive. Calling
`ResearchDatasetEvidence.model_validate` or attaching that evidence to either `ForwardScore` or
`CrossSectionalForwardScore` accepts the invalid nested report: the evidence model reruns its
after-validator but skips field validation on model instances. Direct `ResearchDataset`
construction similarly checks only the report verdict/source and accepts the invalid report.

ADR-156 already makes normally constructed reports defensive and deeply immutable. Additional
freeze containers do not address this bypass; the missing operation is complete validation of
the evidence identity before consumers accept it.

The test-first reproduction produced 14 failures: naive/mixed intervals, UTC normalization,
unchecked nested reports through all three evidence consumers, and direct dataset replacements.
A read-only audit found 12 committed forward-evidence records in the single-name paper book and
cross-sectional pool; all requested intervals were timezone-aware.

## Required correction

Revalidate evidence model instances, require aware acquisition bounds and normalize them to UTC,
and reconstruct direct dataset identity through the same evidence boundary. Retain the validated
report snapshot. Preserve JSON shapes, nullable legacy score evidence, and existing quality and
methodology rules. Mutable frame ownership and unchecked copies of entire outer scores require
separate review; this finding does not claim to resolve them.

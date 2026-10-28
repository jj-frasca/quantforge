# FINDING-335: Fundamental records do not retain their filing envelope

- **Status:** Supplied history citations retained prospectively (ADR-399); legacy unknown and as-of/per-fact limits remain
- **Date:** 2026-10-28, Codex autonomous session14 (ISO2026-W44)
- **Producing revision:** 2fff8226
- **Affected:** FundamentalRecord, compute_fundamental_record, merge_fundamental_records
- **Related:** ADR-022/029/155; distinct from FINDING-087/317/322

## Evidence

FundamentalsHistory contains entity_name, form, accession_number, source_url and
source. compute_fundamental_record retains none of those fields. Two histories
with identical numeric rows, symbol, CIK and fiscal-year labels but different
filing envelopes produce identical complete FundamentalRecord JSON, both without
valuation and with it. Independent data and research reviews reproduce the gap.
The schema contains symbol, CIK, fiscal_year, scores, flags and optional SIC
fields; it has no filing citation or observation/availability timestamp.

score_valuation preserves entity/form/accession/URL differences in its own model,
but compute_fundamental_record retains only the value scalar and flags. The
valuation model separately defaults source to SEC EDGAR rather than copying
history.source; that source-label limitation is not corrected here.

This makes the record module's claim that every score cites its filing false.
An empty flags list cannot recover that citation. Fiscal_year is the last
selected row's label, not an established as-of time. Merge compares only those
labels: higher fiscal year wins and incoming wins ties. Neither accession nor
filing/availability time participates, so "keep the newest filing" overstates
the implemented selection. No actual stale replacement or affected company is
established by the synthetic collision.

## Reproduction

Run from backend with its existing environment; no services are called:

This reproduces the gap at producing revision2fff8226 and reporting revision
9e51e3a8. ADR-399's later retention changes the producer contract prospectively.

```python
from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.record import compute_fundamental_record
from app.research.valuation.score import score_valuation

years = tuple(AnnualFundamentals(fiscal_year=y, revenue=100, eps=2,
    shares_diluted=10) for y in (2024, 2025))
a = FundamentalsHistory(symbol="SYNTH", cik=1, entity_name="A", form="10-K",
    accession_number="a", source_url="https://example.invalid/a", years=years)
b = a.model_copy(update={"entity_name": "B", "form": "10-K/A",
    "accession_number": "b", "source_url": "https://example.invalid/b",
    "source": "Synthetic other source"})
for price in (None, 55.0):
    assert compute_fundamental_record(a, price).model_dump_json() == (
        compute_fundamental_record(b, price).model_dump_json())
assert score_valuation(a, 55).source_url != score_valuation(b, 55).source_url
```

## Bounded response and limits

The initial reporting correction qualifies docstrings and cold contracts to describe company score snapshots
labelled by the latest selected fiscal year, without retained filing citations
or an established as-of time. Describe the actual higher-year/incoming-tie merge.
This is a reporting correction, with no scoring, schema field, merge, threshold,
provider or persistence behavior change. No new runtime decision is adopted.

The subsequent ADR-399 below adopts nullable envelope retention with separate TDD,
legacy-absence and consumer-binding policy. A retained supplied-history envelope does not
establish every input fact's accession, accounting period, availability date,
economic consistency or point-in-time validity. F322 remains separate; retaining
source metadata cannot repair its physical-period selection problem. Historical
records cannot acquire missing citations by guessing from company/year or current
source responses. No generated file, source fetch, search/cohort, fingerprint,
accounting-v14 or validation threshold changes.

## Verification

Before editing, freeze108 complete record claims,4 merge payloads, the model schema
and the whole record-module AST. Parent and both independent reviewers preserve
all claims/merges exactly, schema except its root description, and AST except the
four declared docstrings. The published reproduction passes independently; parent,
research and data each pass38 existing synthetic record tests. Both final reviews
approve. An initial parent command names a nonexistent additional test file and
runs zero tests; it is excluded from verification. Foreground full gate and exact
publication CI receipts are recorded separately in the session ledger. No runtime
TDD claim is made for this documentation-only correction.

## Supplied-history retention (ADR-399)

After the reporting correction's exact CI succeeds, ADR-399 adopts a separate
runtime decision: retain the seven supplied company/envelope scalars in nullable
frozen history_citation, with strict nested validation and outer symbol/CIK binding.
None means unknown/unretained and is omitted from serialization, preserving legacy
absence. Empty histories retain their supplied metadata without inventing facts or
an as-of date. Existing score computation and whole-winner merge remain; an incoming
legacy tie can replace attribution with unknown. No citation is inferred for old
rows. Older writers may discard the field.

This addresses future supplied-envelope loss only. It does not establish filing
freshness, per-fact provenance, source authenticity, periods, availability/PIT,
price provenance or producing code; valuation's separate source default remains.
Actual pre-code execution has67 failures and3 passing controls across70 new tests,
without collection errors. Parent and both independent reviewers pass108 focused
synthetic tests and approve. Both replay108 producer claims outside the citation,
108 legacy JSON claims,4 merge payloads, all4258 generated rows and their raw file
hash unchanged. The whole record-module AST outside four frozen additions and
four docstrings matches exactly; existing record-test AST changes only its leading
documentation. Generated evidence is read-only. The deliberate forged nested scalar
test emits a serializer warning before merge reconstruction rejects it.

For the same supplied histories a and b above, the ADR-399 producer instead satisfies:

```python
for price in (None, 55.0):
    left = compute_fundamental_record(a, price).model_dump(round_trip=True)
    right = compute_fundamental_record(b, price).model_dump(round_trip=True)
    assert left.pop("history_citation")["source_url"] == a.source_url
    assert right.pop("history_citation")["source"] == b.source
    assert left == right  # all previous numeric, identity and flag claims persist
```

Full foreground gate and exact publication CI receipts are recorded separately
in the session ledger; this adds no historical reconstruction or source-truth claim.

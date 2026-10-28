# FINDING-335: Fundamental records do not retain their filing envelope

- **Status:** Open; reporting qualified, runtime provenance retention deferred
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

Qualify present docstrings and cold contracts to describe company score snapshots
labelled by the latest selected fiscal year, without retained filing citations
or an established as-of time. Describe the actual higher-year/incoming-tie merge.
This is a reporting correction, with no scoring, schema field, merge, threshold,
provider or persistence behavior change. No new runtime decision is adopted.

Future nullable envelope retention needs a separate ADR, TDD, legacy-absence and
consumer-binding policy. A retained supplied-history envelope would still not
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

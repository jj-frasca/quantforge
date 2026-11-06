# ADR-419: Retain selected revenue and earnings fact periods

- **Status:** Accepted
- **Date:** 2026-11-06
- **Deciders:** Codex W45 session3 under standing autonomy
- **Addresses:** FINDING-322 input-evidence loss, not annual/PIT correctness
- **Extends:** ADR-017/022/029/399; relates to ADR-116/117/417/418

## Context and economic purpose

Frozen full AAPL and MSFT CompanyFacts payloads demonstrate historical quarters
selected as annual revenue, net income and EPS (FINDING-322). These feed quality
ratios and own-history valuation percentiles. Present models lose which selected
source periods produced those inputs; the latest whole-history citation cannot
establish each fact's observation period or filed label. A duration-only change to
the shared selector would also affect instantaneous balances and still misassign
annual comparatives. Data review recommends one three-flow input capability before
one coherent annual/instant/availability policy. This is not another scorecard or
an orphan helper: evidence must reach new FundamentalRecord output naturally.

## Decision and precise scope

Retain selected revenue/net_income/EPS source identity together for every parsed
revenue-anchored year. Add frozen revalidated models:

- SelectedFlowFact: actual selected `tag`, requested `unit`, and detached immutable
  finite JSON `row` containing only ORIGINAL PRESENT fy/fp/form/filed/accn/start/
  end/frame/val keys. Preserve absence versus null and original JSON types/values.
- SelectedFlowFacts: nullable revenue, net_income and eps facts; unknown facts
  omitted. This makes no claim about shares, balances, OCF/capex, derived FCF/GP
  or other unretained concepts.
- AnnualFlowFacts: the enclosing normalized fiscal-year label and nullable facts.

AnnualFundamentals gains optional flow_facts=None, unknown omitted on dumps.
FundamentalRecord gains optional flow_fact_history=None. New compute results copy
one ordered year entry per supplied history year whenever any flow evidence is
known; keep unknown years explicit. Entirely unknown/direct/legacy histories omit
the new record field, including empty histories. No later source lookup or copying
from another year/filer/winner. Existing symbol/CIK whole-history citation remains.

Keep _annual_facts unchanged. A small history-only adapter walks the same ordered
tags, invokes that existing selector per singleton tag, and constructs both old
scalar inputs and new metadata from the SAME selected row. First matching tag,
FY/10-K filter, latest-filed/input-order ties, reported-year grouping and all numeric
expressions stay. The snapshot parser stays unchanged. This is conditional on
ordinary JSON source mappings, not arbitrary stateful Mapping side effects.

The new metadata boundary accepts only finite JSON-compatible evidence through
the existing shared freeze_json recipe; malformed newly consumed metadata may
refuse instead of being ignored. It does not normalize dates, infer end.year,
choose annual alternatives, certify source authenticity or recover PIT history.
Original row `val` is attribution before the existing float projection, not a
new estimator or exact-real numerical correction. Data retained are claims from
the supplied source, not authenticated financial facts.

Attach to FundamentalRecord after existing scoring and citation construction;
retain current computation/error order before attachment. Keep complete winning
record through existing higher-year/incoming-tie merge. A legacy winning tie may
lose known evidence; never borrow a losing row's metadata. Older writers may drop
new optional fields. Historical generated JSON, source fixtures, ADR-417 receipts
and ADR-418 cohort/input hashes remain untouched; no backfill or cohort refresh.

## Hypothesis, comparison and acceptance before implementation

This is input-provenance production work, not a new market experiment. Zero price
acquisitions, searches, parameter trials, return comparisons or threshold changes.
Acceptance: on both immutable full-source fixtures, exact selected tags, units,
raw metadata/absence and source values survive parser -> record -> JSON -> merge.
All old numeric/history/snapshot/record claims must match the baseline after
excluding only the declared optional additions. Synthetic same-filed mixed-period
input order must move scalar and source row together. Legacy omission, missing
NI/EPS, direct unknown history and immutable detached evidence must remain honest.
Observe RED before code, use source-grounded TDD plus a permutation/row-binding
property, independent data/research reviews and full foreground gates.

This cannot improve the alpha case by itself. It exposes evidence needed to
choose an annual-flow/PIT policy; it repairs neither actual quarters nor old
scores. All prior research/trial accounting and validation thresholds stay.
The prospective portfolio continues using its already sealed opaque input bytes.

## Capacity, alternatives and reversal

Retaining all17 concepts was rejected as unnecessary breadth. A shared annual
filter and end-year relabeling were rejected for unsupported fiscal/instant and
comparative assumptions. Two chosen frozen examples previously estimated roughly
28–36MB additional pretty JSON at4,260 filers for metadata without val; the final
representation must be measured, not advertised as a universal100MB capacity
bound. Longer histories/full SEC coverage may require separately reviewed compact
or sharded storage; never silently truncate evidence or history. Do not redesign
storage in this slice on a hypothetical extrapolation alone.

Removing new optional producer fields reverses capability but never authorizes
erasing generated evidence. After this one three-flow capability, pursue ONE
coherent evidence-backed period/availability policy or a measured economic task;
do not repeat an attribution-field chain across all remaining concepts.

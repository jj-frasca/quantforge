# ADR-421: Evaluate explicitly anchored annual fundamentals

- **Status:** Accepted
- **Date:** 2026-11-07
- **Deciders:** Codex W45 session7 under standing autonomy
- **Extends:** ADR017/022/029/116/117/399/419/420; FINDING322

## Context and pre-adoption review

The current research/paper evidence has no ADR018 survivor and no mature retained
paper position. Quality/value needs truthful input periods before a historical
portfolio gate is meaningful. FY/form labels can select a quarter; a duration
band cannot validate balances, fiscal calendars or historical availability.
Independent research and data reviews approved this design before implementation
or new actual selection. The existing original-filing anchor supports one year;
comparative-year fiscal labels must not be invented from it.

## Decision and source contract

Add a separate network-free opt-in evaluator for ONE externally audited original
annual anchor and ONE retained CompanyFacts byte capture. Its result retains
history, existing no-price FundamentalRecord, all admitted source rows/missing
fields, anchor and both source provenance records. Existing parser, source adapter,
sweep, scorers, generated records and frozen protocols remain untouched.

A caller supplies an anchor with positive issuer CIK, accession, fiscal label,
annual start/report end, exact original10-K/FY/nontransition declarations,
original-source URL/SHA256/aware completed-observation time and raw header labels.
These are external audited claims, not certification merely from schema validity.
Do not infer anchors from fy/fp/frame/end.year, longest duration or latest filing.
Reject invalid dates/identity. Single-anchor scope prevents invented comparative
years, duplicate annual labels and unsupported trend continuity. Multiple-year
construction is outside this decision; no per-accession acquisition chain.

CompanyFacts provenance requires URL, SHA256 and aware completed-observation time;
hash actual supplied bytes before JSON selection and require issuer agreement.
The as-of instant must be aware and >= max(both observed times), normalizedUTC.
This is an observed-source bound, NEVER first public availability, acceptance
conversion, historical2019PIT or a restatement cutoff. Raw filed/acceptance/change
labels remain unzoned original claims. A capture in2026 is unavailable to a2019
query. Removing later rows does not reconstruct a past vendor vintage.

Select from exact form10-K, exact accession and appropriate units. Every flow
(revenue, NI, EPS, weighted-average diluted shares, OCF, capex, GP, COGS) must match
the exact anchor start AND end. Every instant (assets/current assets/current
liabilities/long-term debt/retained earnings/equity) must match report end and
have NO start key; explicit null start is unsupported, not an instant shortcut.
Ignore fy/fp/frame for eligibility, preserve original-present row metadata.
Use existing ordered tag/unit fallbacks among tags with eligible rows. All eligible
values in the first eligible tag must agree EXACTLY before float conversion;
reject boolean/non-numeric/nonfinite values or disagreement. Preserve all agreeing
rows in canonical JSON order including duplicates; permutation cannot choose a
winner. Do not borrow another accession, quarter, comparative or fallback after
contradiction. Revenue missing refuses; optional fields missing remainNone with
explicit statuses. GP direct precedes revenue-minus-COGS fallback; FCF requires
both OCF and capex. Reject nonfinite projections/derived values, no numerical
recovery. No price join. Existing no-price scorer consumes the one-year history
inside the returned evidence wrapper; value/combined stayNone and existing
one-year F-score behavior remains qualified as insufficient history.

This matches later aggregate CompanyFacts claims to a supplied audited annual
anchor. It DOES NOT independently parse/certify every original XBRL fact, entity
context, fiscal-transition interpretation or EPS/share split basis. ADR420 audited
original revenue only. Do not promote this result as a PIT portfolio input panel.

## Hypothesis, comparison and acceptance fixed before implementation

Hypothesis: explicit annual/accession matching removes the known quarter choice
while aligned balances and actual observation bounds remain usable by the existing
scorer. Fix only the frozen AAPL CompanyFacts and ADR420 FY2019 known witness from
FINDING322; original annual2018-09-30..2019-09-28, accession0000320193-19-000119.
No new source request, rank, market price or economic outcome. Compare all fields
and missingness with legacy FY2019; annual revenue must be260174000000 vs64040000000.
Any required absence/conflict is a qualified negative, never a changed criterion.

Tests FIRST: actual collected RED, then narrow implementation. Cover exact flow/
instant boundaries, non-December fiscal year, weighted shares, fallbacks, malformed/
conflicting duplicates, optional absence, source SHA/issuer/anchor/cutoff refusal,
permutation and derived-operand properties, detached evidence and no-price scorer
integration. Preserve old parser/scorer outcomes and source/cohort bytes exactly.
Independent final research/data reviews and foreground make check-all precede
individual publication and exact CI.

Zero new market/configuration trials, financed accounts or return comparisons.
No untouched return geometry exists here. Costs/resources$0, no new acquisition.
PBO/DSR/WF/holdout/graduation remain NOT MEASURED. Prior technical and quality/value
selection, ADR414–416, terminal417 and future418 remain recorded/frozen; effectiveN
is not reset. This can improve one input capability, never alpha by itself.

## Alternatives, consequences and reversal

Duration bands are simpler but cannot validate fiscal identity/instants/PIT.
Default-parser replacement would affect all users before broad input support.
More metadata alone exposes a defect without resolving the aligned account input.
The opt-in policy is narrower and may refuse or omit fields; it deliberately
cannot produce a full historical gate. Future work needs a separately reviewed
multi-issuer prospectively observed history and untouched economic geometry, not
another filing-witness capture chain. Removing the evaluator reverses capability
without erasing any generated, archived or frozen evidence.

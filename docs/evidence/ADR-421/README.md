# One anchored annual input, no new alpha evidence

ADR-421 evaluates the already-frozen known AAPL FY2019 witness with an explicit
original-filing annual interval and an observed-source availability bound. No
source was requested, no price was joined and no return was evaluated. This is a
conditional input capability, not a historical PIT panel or a repaired default feed.

| FY2019 input | Unchanged legacy selector | Explicit annual anchor |
|---|---:|---:|
| Revenue USD | 64,040,000,000 | 260,174,000,000 |
| Net income USD | 13,686,000,000 | 55,256,000,000 |
| Diluted EPS USD/share | 3.03 | 11.89 |
| Gross profit USD | 24,313,000,000 | 98,392,000,000 |

The other nine populated financial scalars match the legacy FY2019 row; price
remains absent. All 14 raw
concepts (including GP and COGS, OCF and capex) have one admitted same-accession
row. No optional source field is missing in this selected witness. FCF is58.896bn,
assets338.516bn, and weighted-average diluted shares4,648,913,000. Full values,
original rows, units, raw labels, source digests and no-price scorer output are in
[result.json](result.json). The source comparison and acceptance were fixed in
[ADR-421](../../adr/ADR-421-evaluate-explicitly-anchored-fundamentals.md) and the
FINDING322 addendum before implementation/new selection.

The observed-source eligibility bound is **2026-11-06T23:31:19.474972Z**, the later
of the two actual capture completions. A2019 query refuses. No header acceptance,
filed or changed label was converted to a public-availability instant. The original
2019 financial statement was captured in2026. Later aggregate CompanyFacts rows
are matched by accession/interval, not independently authenticated original facts.
ADR420 independently checked original revenue only; EPS/share adjustment basis,
other original contexts, issuer truth, amendments and general coverage remain
uncertified. No comparative-year anchor was invented from the2019 filing.

The existing no-price scorer consumes the aligned one-year history inside its
retained wrapper. It reports gross profitability0.2906568670 and a heuristic
quality score0.3916249227. Those are conditional accounting outputs, not evidence
of investable quality or alpha. Its one-year F-score0 is the existing
insufficient-history behavior; empty flags do not establish completeness.
Value and combined scores remain null. No gross/net return, financing, exposure,
turnover, drawdown, benchmark, PBO/DSR/WF/holdout/graduation is measured.

Zero new market/configuration trials; prior related technical/quality/value
selection and ADR414–416 remain disclosed. ADR417 is permanently UNEVALUABLE,
ADR418's sealed future inputs/geometry remain unchanged. No effective-N reset,
old-source retry, threshold change or generated-data write. Resources/acquisition$0.
The alpha case **did not improve**. The input case improved for one deliberately
selected known defect; this is not an incidence estimate.

## Reproduce offline

From the repository root, using the existing project interpreter; no network,
root modification, data writer or source fetch occurs:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import gzip, json
from datetime import datetime
from pathlib import Path
from app.data.anchored_fundamentals import (
    FilingAnnualAnchor, SourceObservation, evaluate_anchored_fundamentals,
)
from app.data.fundamentals import parse_company_facts_history
p = Path('docs/evidence/ADR-421')
r = json.loads((p/'request.json').read_text())
raw = gzip.decompress(Path(r['companyfacts_path']).read_bytes())
result = evaluate_anchored_fundamentals(
    raw=raw, symbol=r['symbol'],
    observation=SourceObservation.model_validate_json(json.dumps(r['observation'])),
    anchor=FilingAnnualAnchor.model_validate_json(json.dumps(r['anchor'])),
    as_of=datetime.fromisoformat(r['as_of']),
)
legacy = next(y for y in parse_company_facts_history(json.loads(raw), 'AAPL').years
              if y.fiscal_year == 2019)
expected = json.loads((p/'result.json').read_text())
assert result.model_dump(mode='json') == expected['anchored']
assert legacy.model_dump(mode='json') == expected['legacy_fy2019']
print('Complete anchored wrapper and unchanged legacy FY2019 result match')
PY
```

[request.json](request.json) supplies the fixed external audited anchor and both
capture receipts. Original financial components, full-source receipt and DEI audit
remain in [ADR420 evidence](../FINDING-322/AAPL-2019-original-filing/README.md).
The original full-body digest identifies the permanently retained source, while
the portable complete10-K component has its own distinct declared hash. This
API consumes the supplied anchor; schema validation does not perform that audit.

Next economic experiment: close ADR418 exactly once in its already registered
February11 window, without interim economics. For a later full-gate study, first
register a finite multi-issuer coverage/availability study using prospectively
observed anchored inputs and explicit missingness; then freeze sufficient untouched
returns and costs. Do not backdate these2026 captures, redraw ADR418, repeat the
failed ADR417 acquisition, or start an accession-by-accession evidence chain.

## Verification receipts

`verification.tar.gz` preserves both independent pre-adoption reviews, final
implementation/result reviews, the pre-code baseline (658 protected file hashes
and two complete old history/record claims), and actual test receipts. The first
31 collected tests failed on the absent module before implementation. An added
control then exposed exact-value spelling changing under equal int/decimal row
reordering (1 failure/34 controls); canonical representation corrected that.
Final focused verification passes38 tests, including two Hypothesis properties.
A later new test initially expected the wrong refusal message for an enormous
Decimal projection; only its regex was corrected to the actual valid nonfinite
refusal. No scientific threshold or old test was changed. `manifest.json` binds
source, test, request, result and archive hashes. Independent reviewers reproduced
all14 source-domain selections, original annual-anchor linkage and all protected
baseline claims without source acquisition.

The supplied nontransition declaration also has explicit retained cover evidence.
An additional independent offline inspection found one checked
`dei:DocumentAnnualReport` and one unchecked `dei:DocumentTransitionReport`, both
in `FD2019Q4YTD`, with declared `ixt-sec:boolballotbox` formatting. Exact nodes,
attributes, interpretations and original component hashes are preserved in
`annual-cover-review.json`. This additional inspection is separate from ADR420's
original four-DEI/revenue linkage audit; no source was fetched again.

Release verification: foreground `make check-all PYTEST_WORKERS=1` exited0;
17,862 backend tests passed in502.37s (97.52% coverage from11,067 statements /
274 misses),781 frontend tests passed (97.89% statements). Ruff557files and
mypy198sources passed. Full log is included in the verification archive.

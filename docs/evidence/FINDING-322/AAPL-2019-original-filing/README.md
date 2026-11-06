# Original filing anchor for the known FY2019 quarter witness

**Source linkage PASS under ADR-420; alpha evidence unchanged.** The single
registered request captured the original Apple accession already identified in
FINDING-322. Its own inline XBRL annual context and DEI fiscal labels distinguish
the known annual revenue from the quarter selected by the existing history
parser. No parser, score, portfolio, threshold or generated record changes here.

The exact [SEC complete-submission source](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119.txt)
was requested once, without retry, redirect, fallback, keys or paid service.
`START.json` and `RESULT.json` retain the actual execution/transport receipt.
`PREACQUISITION.json` binds the accepted protocol, final methods, tests and reviews
before target content was fetched. The root is permanently frozen at
`/tmp/qf-w45-s5-original-aapl2019`; never request it again under this protocol.

| Receipt | Value |
|---|---|
| Actual HTTP start (UTC) | 2026-11-06T23:31:18.538713+00:00 |
| Receipt completion (UTC) | 2026-11-06T23:31:19.474972+00:00 |
| HTTP status | 200 |
| Complete retained decoded body | 12,861,616 bytes |
| Complete body SHA256 | `c77a7ab405b61398dcbd7b0ecb98191b24c9519d9b18689c280c2ac7e4ebf4ab` |
| Complete body gzip (root only) | 1,437,549 bytes; SHA256 `5510129c3e7ef001dce314e917a52238a93027a94d35b59495cd757db36aa6d0` |
| Accepted protocol SHA256 | `8d303f98bd1f507962dc88a8f0fb36e125fb4f2c0d732b5e71fa44a7161c5412` |
| Pre-acquisition method archive | 22,706 bytes; SHA256 `7ff3c473693f8647a5e3eae5f3cad8984746a56bac1e25f66bf2f78a01baf322` |

## What the filing actually supplies

Header: CIK 0000320193, accession 0000320193-19-000119, form 10-K, conformed
report end 20190928. Raw acceptance label is **20191030181236**, filed-as-of date
**20191031**, date-as-of-change **20191030**. These are distinct supplied labels;
no UTC conversion or first-public-availability inference is made. This 2026 capture
is not a contemporaneous 2019 vendor vintage and cannot prove PIT completeness.

The submission contains 96 inventoried DOCUMENT blocks. There is no EX-101.INS
role; the frozen audit uses the primary 10-K `a10-k20199282019.htm`, rather than
silently treating a later XML-role document as the registered standalone branch.
It resolves 301 contexts, 9 units, 62 revenue candidates and 4 required DEI facts.

All 4 DEI facts bind **FD2019Q4YTD**, a dimensionless issuer 320193 duration context
from 2018-09-30 through 2019-09-28: DocumentType 10-K, DocumentFiscalYearFocus 2019,
DocumentFiscalPeriodFocus FY and DocumentPeriodEndDate September 28, 2019 (declared
`ixt:datemonthdayyearen`). This supplies an actual annual anchor without a guessed
duration band, longest-span choice, end.year mapping or frame requirement.

| Role | Context | Original period | Raw displayed amount / scale | Exact USD |
|---|---|---|---|---:|
| Annual (3 agreeing occurrences) | FD2019Q4YTD | 2018-09-30 to 2019-09-28 | 260,174 /6 | 260,174,000,000 |
| Quarter (1 occurrence) | FD2019Q4QTD | 2019-06-30 to 2019-09-28 | 64,040 /6 | 64,040,000,000 |

Both use `RevenueFromContractWithCustomerExcludingAssessedTax`, declared
`ixt:numdotdecimal`, unit `usd` resolving to ISO4217 USD, the same issuer, and no
dimensions/scenario. All matching admitted occurrences agree. Dimensional and
other-period candidates remain inventoried; none is selected to make the result
pass. Exact fact IDs, source attributes/text/XML, contexts and units are retained
in `AUDIT.json.gz`.

## Repository scope and offline verification

`COMPONENTS.json` gives original/compressed sizes and SHA256 for the exact header,
footer and **complete primary 10-K DOCUMENT block**. Its gzip is 179,177 bytes,
well below the fixed 450 KiB component limit. No component was split or truncated.
The full 12.86 MB response and all unrelated exhibits remain root-retained; this
folder explicitly preserves financial analysis components, **not the entire
unmodified submission**. `INVENTORY.json` retains all 96 original block hashes.

`method.tar.gz` preserves exact pre-acquisition scripts/tests/reviews and RED/GREEN
receipts. The acquisition draft/collection sequencing mistake is disclosed there
and in the finding; later missing-target controls are not called pre-code RED.
Genuine acquisition behavioral REDs preceded two fixes. The independent audit
used an 18-case failing stub and later genuine 2/3/4-case REDs before precision,
dimension, SGML-wrapper, inline-exclude, root and availability corrections. Final
17 acquisition +28 audit tests pass, including 80 Hypothesis exact-Fraction cases.
Neither evidence audit imports nor offline tests perform source requests.
`result-review.tar.gz` preserves both independent actual-source reviews and their
offline audit scripts (SHA256 `c2b40edfa1af689ce9df89e4666a168f3031dae4a35788592942f1569c5a226f`).

From the repository root, this **no-network** command verifies every published
component, the original inventory, frozen method identity and the exact financial
result using only the published primary component. A reconstructed thin submission
has 1 DOCUMENT instead of 96 and a different whole-body hash; those differences are
explicitly excluded from the comparison. Financial/header/context results match.

```sh
python3 - <<'PY'
from pathlib import Path
import gzip, hashlib, importlib.util, json, tarfile, tempfile
p = Path('docs/evidence/FINDING-322/AAPL-2019-original-filing')
components = json.loads((p/'COMPONENTS.json').read_text())
pre = json.loads((p/'PREACQUISITION.json').read_text())
actual = json.loads(gzip.decompress((p/'AUDIT.json.gz').read_bytes()))
receipt = json.loads((p/'RESULT.json').read_text())
assert components['not_portable'] == []
assert receipt['raw_sha256'] == components['full_source_raw_sha256'] == actual['source_sha256']
assert json.loads((p/'INVENTORY.json').read_text()) == actual['inventory']
bodies = {}
for item in components['components']:
    packed = (p/item['file']).read_bytes()
    body = gzip.decompress(packed)
    assert len(packed) == item['gzip_bytes'] and len(body) == item['raw_bytes']
    assert hashlib.sha256(packed).hexdigest() == item['gzip_sha256']
    assert hashlib.sha256(body).hexdigest() == item['raw_sha256']
    bodies[item['file']] = body
thin = bodies['submission-header.raw.gz'] + bodies['document-000.10-k.sgml.gz'] + bodies['submission-footer.raw.gz']
with tempfile.TemporaryDirectory() as work:
    script = Path(work)/'audit420.py'
    with tarfile.open(p/'method.tar.gz', 'r:gz') as archive:
        code = archive.extractfile('qf-w45-s5-audit420.py').read()
    assert hashlib.sha256(code).hexdigest() == pre['files']['qf-w45-s5-audit420.py']['sha256']
    script.write_bytes(code)
    spec = importlib.util.spec_from_file_location('audit420', script)
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    replay = json.loads(json.dumps(api.audit(thin)))
for field in ('header', 'documents', 'representation', 'linkage', 'reasons'):
    assert replay[field] == actual[field], field
assert replay['counts']['documents'] == 1 and actual['counts']['documents'] == 96
assert replay['counts']['revenue_candidates'] == actual['counts']['revenue_candidates'] == 62
assert replay['counts']['dei_candidates'] == actual['counts']['dei_candidates'] == 4
assert replay['linkage'] == 'PASS'
print('Published complete financial component reproduces source-only linkage PASS')
PY
```

This selected witness is not population calibration, an annual/instant selection
policy, a fiscal-year mapper, a corrected quality score, an authentic historical
availability panel or alpha. No returns, costs, drawdown, DSR/PBO/WF or graduation
were measured. The next useful input task is one integrated opt-in selection policy
using explicit filing anchors for flows, matching instant balance dates and
conservative availability labels, with unsupported/ambiguous inputs explicit.
Any later economic experiment needs separately registered untouched geometry and
prior-trial accounting. ADR-417 and ADR-418 remain frozen and unchanged.

# Conditional beginning-assets ROA: retained-source production comparison

This is the known Apple FY2021/22 witness from FINDING324, evaluated through the
actual scorer, quality blend and no-price record under ADR423. Its outcome was
specified before implementation. It is not untouched OOS evidence, a portfolio
backtest or complete Piotroski replication. No new source or return cohort was
acquired; ADR422 remains permanently expired and all other frozen studies stay.

| Actual consumed result | Default closing Assets | Explicit beginning Assets |
|---|---:|---:|
| Prior ROA | 47340/175501 | 11835/40486 |
| Latest ROA | 99803/352755 | 99803/351002 |
| Improving ROA | true | false |
| F-score | 8 | 7 |
| Quality blend | 0.6675842309900554 | 0.6305471939530184 |

The other eight F-score verdicts, gross profitability and safety match exactly.
The scorer computes the actual ratios using the selected denominators; no point
is subtracted afterward. Reported Fraction strings rationalize consumed binary64
operands; they also match the exact source integer ratios in this particular
witness. They do not generally certify exact decimal source arithmetic.

`request.json` fixes the original capture SHA/URL/observation, two explicit
interval assertions, earliest closing accession and unchanged history prefix.
`result.json` retains the full supplied history, seven source groups, all raw row
keys, exact decimal values, source observation, history hash, default and opt-in
FScore/QualityScore/Record and ratio comparison. Optional evidence travels through
quality and record and survives actual existing pool/shard JSON readers. It is
omitted from every evidence-absent legacy record. Explicit priced mode refuses.

The full captured CompanyFacts response was observed October30,2026. As-of is
that inherited completed-observation claim, not first public availability or a
2022 vintage. The supplied history retains its original **2025 accession**;
separate2021/22 ROA evidence does not relabel unrelated fields. Its FY2020
revenue-derived period_end happens to equal the Assets closing date, but this
coincidence does not certify balance timing or annual income. ROA geometry comes
from independently matched income and Assets groups, not that revenue field.
Explicit interval assertions are not original-DEI audits. NetIncomeLoss remains
conditional; equivalence to the paper's numerator is unproved. Other component
periods, turnover interpretation, diluted-share issuance and split basis remain
unverified. Direct evidence models are supplied claims; only the outer evaluator
checks actual byte-to-row linkage, without certifying issuer truth.

**Alpha evidence did not improve.** One demonstrated scoring mismatch now has an
attributed opt-in evaluation; defaults and historical scores remain unchanged.
Zero new economic/configuration trials, no effective-N reset or pooling, $0 paid
resources. No account, costs/fills, return geometry, exposure, turnover, drawdown
or benchmarks were measured. PBO/DSR/WF/holdout/graduation remain NOT MEASURED.
The next actual economic experiment remains ADR418's already sealed February11,
2027 final screen under its original account/costs/window, with no interim look.
A full portfolio gate still needs truthful dated inputs and sufficient untouched
geometry; this result supplies neither by itself.

## Verification receipts

Before implementation,22 complete default histories/claims,4260 legacy record
round-trips and1039 protected data/evidence/old-test hashes were frozen.
`baseline.json.gz` retains the entire checkpoint; `manifest.json` binds its raw
hash, exact source/test/protocol/dependency hashes and unchanged AST members.
`verification-receipts.tar.gz` retains original quality/record source+AST snapshots,
baseline capture code, actual RED/GREEN logs, focused956PASS and lint/type receipt.
Original source snapshots match Git basea22fc109. The baseline gzip is480080 bytes,
below the unchanged500KiB large-file hook; it is complete, not split or truncated.
The separate receipt archive is a distinct verification artifact, not a split of
that checkpoint. Original complete source bytes remain in FINDING322's fixture.

TDD chronology: corrected29 collected failures preceded implementation. Initial
synthetic fixtures omitted required revenue, causing14 misleading refusal passes;
the fixture was corrected before source existed, then29 tests failed on missing
implementation. Both logs are retained. The first actual-source test reserialized
JSON; before an actual artifact claim it was corrected to consume the original
raw bytes with their real SHA/observation. Additional exact-before-projection and
decimal-order controls failed2cases before fixes; nonzero-to-zero projection
controls failed2 before fixes. The real JSON reader test then failed before
canonical ISO date/time and JSON-array materialization were added only to the new
evidence models. Final48 new tests and956 focused tests passed. No old test,
source capture, financial threshold or frozen cohort was changed to obtain green.
Independent final reviews are retained alongside this README.

## Offline reproduction

Run from the repository root at the producing implementation. This executes no
network or live entry point and compares the complete retained result:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import gzip, hashlib, json
from datetime import datetime
from pathlib import Path
from app.data.fundamentals import FundamentalsHistory, parse_company_facts_history
from app.data.roa_evidence import ROAClosing, ROAInterval, ROAObservation
from app.research.fundamentals.roa_evaluation import evaluate_beginning_assets_roa
p = Path('docs/evidence/ADR-423')
r = json.loads((p / 'request.json').read_text())
raw = gzip.decompress(Path(r['source_path']).read_bytes())
assert hashlib.sha256(raw).hexdigest() == r['source_observation']['sha256']
whole = parse_company_facts_history(json.loads(raw), r['symbol'])
history = FundamentalsHistory.model_validate({
    **whole.model_dump(), 'years': [y for y in whole.years if y.fiscal_year <= 2022]
})
result = evaluate_beginning_assets_roa(
    raw=raw, history=history,
    intervals=tuple(ROAInterval.model_validate(i) for i in r['intervals']),
    earliest=ROAClosing.model_validate(r['earliest']),
    observation=ROAObservation.model_validate(r['source_observation']),
    as_of=datetime.fromisoformat(r['as_of']),
)
assert result.model_dump(mode='json') == json.loads((p / 'result.json').read_text())
m = json.loads((p / 'manifest.json').read_text())
for name, expected in m['artifact_sha256'].items():
    assert hashlib.sha256((p / name).read_bytes()).hexdigest() == expected
for name, expected in m['source_code_sha256'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
print('PASS: complete known-witness result and frozen implementation identities')
PY
```

The historical checkpoint capture program scans tracked paths at capture time.
For post-commit verification use the checkpoint's frozen1039 path keys, rather
than adding newly tracked423 files to that historical denominator. On the matching
producing checkout, reproduce every default producer claim and record as follows:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import gzip, hashlib, json
from pathlib import Path
from app.data.fundamentals import FundamentalsHistory
from app.research.fundamentals.quality import piotroski_f_score, quality_score
from app.research.fundamentals.record import FundamentalRecord, compute_fundamental_record
b = json.loads(gzip.decompress(Path('docs/evidence/ADR-423/baseline.json.gz').read_bytes()))
for c in b['claims']:
    h = FundamentalsHistory.model_validate(c['history'])
    assert piotroski_f_score(h).model_dump(mode='json') == c['f']
    assert quality_score(h).model_dump(mode='json') == c['q']
    for price in (None, 10.0):
        try:
            actual = compute_fundamental_record(h, price).model_dump(mode='json')
        except Exception as exc:
            actual = {'error': type(exc).__name__, 'message': str(exc)}
        assert actual == c[str(price)]
rows = json.loads(Path('data/fundamentals_pool.json').read_bytes())
assert [FundamentalRecord.model_validate(r).model_dump(mode='json') for r in rows] == b['legacy']
for name, expected in b['hashes'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
print('PASS: 22 default histories, 4260 legacy records, 1039 frozen path hashes')
PY
```

## Recovery verification (W45 session10)

The inherited implementation and evidence were recovered in place. Fresh
nonimplementing research and data text reviews found no blocker; original runtime
reviews above retain their stated scope. Both complete offline reproduction
blocks passed again. Fresh foreground `make check-all PYTEST_WORKERS=1` passed:
17,910 backend tests (97.44% coverage),781 frontend tests (97.89% statements),
lint, formatting and strict types. The interrupted prior gate had no terminal
receipt and is not counted as verification. No source or outcome was reacquired.

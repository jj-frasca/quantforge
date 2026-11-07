# ADR-422 terminal closure: NOTRUN/EXPIRED

The fixed live-start deadline was **2026-11-07T11:00:00Z**. Recovery in W45
session9 observed UTC18:01:24, the registered source root absent, and the final
PREACQUISITION manifest absent. The inherited ledger stopped during offline
harness preparation. The source study never became eligible to start. No live
invocation was made during recovery. The protocol and fixed roster remain
unchanged; **never renew the window, create another root, retry or replace this
cohort**. This is an expired protocol, not a completed source-coverage failure.

`closure.json` records this local evidence, the original protocol/roster hashes,
archive manifest and all667 protected baseline files matching. Zero recorded
issuer attempts out of five planned is an execution inventory, not a coverage
fraction. Absence of the local root/START and PRE manifest supports the recorded
nonexecution state; it is not an independent audit of SEC server requests.

`expired-offline-work.tar.gz` preserves the exact unfinished scratch method and
tests, initial36-collected-RED log, subsequent targeted RED and GREEN logs,
lint/type receipts, six preparation/review/baseline receipts, original protocol
and roster. Final inherited offline log records67PASS; independent recovery
also ran67PASS. Those synthetic/retained controls were not the five-issuer study.
Earlier conformance notes explicitly were NOT final frozen-harness approval.
There is no approved PRE manifest, target source, live START or coverage result.
The archived harness is historical evidence, **not a shipped capability or a
method authorized for another attempt**. It is not installed into production.
Archive extraction/hash inspection is safe; do not run its live entry point.

No source body is omitted: none was captured for this study. The complete
metadata/method archive is84,751 bytes, below the fixed450KiB packaging cap;
no splitting, truncation or hook bypass occurred. Original source periods,
observed availability, two-year quality completeness and cross-year split-basis
comparability remain unmeasured on this roster. Price/value/combined scores,
financing, turnover/cost accounts, returns, exposure, drawdown, benchmarks and
PBO/DSR/WF/holdout/graduation remain NOT MEASURED. Prior trial accounting is
unchanged; zero new economic trials and zero paid resources. All existing frozen
studies, including ADR417's terminal UNEVALUABLE and ADR418's already sealed future
geometry, remain untouched.

**Alpha case: not improved.** This closure recovers an interrupted protocol and
prevents a deadline violation; it supplies no economic or input-coverage evidence.
The demonstrated quality/value obstacle remains truthful usable input history
and adequate untouched return geometry. Next economic observation remains the
already registered ADR418 final screen on February11,2027; no interim look.
A separately reviewed offline task may assess the existing scorer's comparability
limits using already retained evidence, without new source/return cohorts or
claiming that it completes this expired study.

Verify the receipt and archive without importing or executing the method:

```sh
python3 - <<'PY'
import hashlib, io, json, tarfile
from pathlib import Path
p = Path('docs/evidence/ADR-422')
r = json.loads((p / 'closure.json').read_text())
b = (p / 'expired-offline-work.tar.gz').read_bytes()
assert hashlib.sha256(b).hexdigest() == r['offline_archive_sha256']
assert len(b) == r['offline_archive_bytes'] <= 450 * 1024
with tarfile.open(fileobj=io.BytesIO(b), mode='r:gz') as t:
    assert set(t.getnames()) == set(r['archive_members'])
    for name, expected in r['archive_members'].items():
        assert hashlib.sha256(t.extractfile(name).read()).hexdigest() == expected
assert hashlib.sha256(Path('docs/adr/ADR-422-measure-two-year-quality-input-coverage.md').read_bytes()).hexdigest() == r['protocol_sha256']
assert hashlib.sha256((p / 'roster.json').read_bytes()).hexdigest() == r['roster_sha256']
assert r['status'] == 'NOTRUN/EXPIRED' and r['coverage'] == 'NOT MEASURED'
assert not Path(r['registered_root']).exists()
print('PASS: terminal closure identity; no study execution')
PY
```

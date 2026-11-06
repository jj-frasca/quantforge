# ADR-418 prospective cohort — no outcome

This is an immutable research configuration, not generated portfolio state or
price evidence. Read [ADR-418](../../adr/ADR-418-seal-prospective-quality-value-portfolio.md)
before any use. Never reseal, replace or adjust it after future outcome exposure.

- Input revision: `7048c785fd34fa0fc5b8357fc711929c7fe48fb9`.
- Counts: 4,260 original fundamental records;503 roster names;412 eligible;
  **83 selected**;64 scheduled close labels/63 return intervals.
- Entry2026-11-09 close; exit2027-02-10 close; no prices acquired at sealing.
- Funding and controls: fixed normalized units,10bp entry+exit from capital;
  eligible EW, SPY and cash; one final strict net-excess screen.
- All PBO/DSR/stability/WF/holdout/graduation statuses: NOT MEASURED.
- Complete-source risk remains unresolved;413 series will be required.

`cohort.json.gz` preserves the original eligible JSON records exactly, including
flags/citations/missing provenance, ordered eligibility/selection, full roster,
all64 dates, rules, source account, trial context and pinned input/publication
hashes. No scores were recomputed. The two small publication receipts are read-only
GitHub push-run metadata proving pinned inputs were public before future entry.

SHA256 of compressed artifact:
`2aaf841c39d5dfaae94d56c7a7ef2a312f34cb9a80bb7e36fbcc7d2622031f97`

SHA256 of decompressed canonical JSON:
`14b888b305bd233ef60ff56edd5dd14867d8ed265676908011a866cba18a9c28`

Offline verification (from repository root, no vendor call):

```python
import gzip, hashlib, json, subprocess
from pathlib import Path
p = Path('docs/evidence/ADR-418/cohort.json.gz')
raw = gzip.decompress(p.read_bytes())
assert hashlib.sha256(raw).hexdigest() == '14b888b305bd233ef60ff56edd5dd14867d8ed265676908011a866cba18a9c28'
c = json.loads(raw)
for path, digest in c['input_hashes'].items():
    blob = subprocess.check_output(['git', 'show', c['input_revision'] + ':' + path])
    assert hashlib.sha256(blob).hexdigest() == digest
adr = Path('docs/adr/ADR-418-seal-prospective-quality-value-portfolio.md')
assert hashlib.sha256(adr.read_bytes()).hexdigest() == c['protocol_sha256']
assert len(c['selection']['eligible']) == 412
assert len(c['selection']['selected']) == 83
assert len(c['geometry']['session_labels']) == 64
assert c['evaluation']['gate_status'] == 'NOT MEASURED'
assert not Path(c['source']['attempt_root']).exists()  # during registration only
```

Independent review must also reproduce rank order from the raw pinned scores,
identity uniqueness, original field equality and published calendar. Do not
compute interim study prices/economics. Unrelated workflow exposure is disclosed
without changing selection. There is no new production behavior in this seal.

Publication+exact green CI is required before2026-11-09T14:30Z, otherwise EXPIRED.
One final evaluation only in[2027-02-11T00:00Z,2027-02-12T00:00Z), with fixed root
`/tmp/qf-adr418-prospective-20261109-20270210`, which is absent during registration.
Future implementation/review must enforce deadlines before creating the root or
fetching prices; no new acquisition driver is implemented or executed here.
ADR-417's failed historical cohort is separate, terminal and never reused.

Final independent research and data audits APPROVE: each reconstructed all counts,
original records, ordering/ties, hashes, publication metadata, calendar, account,
deadlines and no-retry rules offline. Data also queried the authoritative two
GitHub run records and matched the saved successful push receipts. The future
attempt root remains absent; no prices, returns or economics were computed.
Publication of this registration with exact green CI is still required; the
input-publication receipts alone do not satisfy the cohort's own deadline.

Fresh foreground make check-all before registration commit:17,813 backend tests,
781 frontend tests,97.50%/97.89% coverage, lint/format/strict types all green.
These implementation gates provide no economic outcome or financial graduation.

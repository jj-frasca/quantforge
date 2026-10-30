# Frozen full CompanyFacts evidence for FINDING-322

This is the complete, unmodified response body from the free official
[SEC Apple CompanyFacts endpoint](https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json),
compressed with gzip and modification time zero. Decompression preserves every
raw byte and array order. It is a historical evidence fixture, not a current
fundamentals feed or a generated `data/` record. Never refresh it in place.

Acquisition: one ordinary request from Codex session21, 2026-W44, using the exact
`USER_AGENT` constant in `backend/scripts/fundamental_sweep.py` at revision
`3018dfd01ab531e7815aed68c75ea1b18f2b0484`; no API key, retry or alternate headers.
The web reader could not access the URL; this fixture came from direct HTTP, not
reader reconstruction. The first shell command failed during Python imports
before making a request; the project interpreter made the sole HTTP request.

| Receipt | Value |
|---|---|
| Request UTC | 2026-10-30T07:28:43.638699+00:00 |
| Completion UTC | 2026-10-30T07:28:44.145492+00:00 |
| HTTP status / content type | 200 / application/json |
| Response Date | Fri, 30 Oct 2026 07:28:43 GMT |
| Original and final URL | Official endpoint linked above |
| Decoded identity | CIK 320193; Apple Inc.; 503 us-gaap concepts |
| Raw length | 3,789,099 bytes |
| Raw SHA-256 | `73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43` |
| Gzip length | 255,521 bytes |
| Gzip SHA-256 | `0ab67c99b477acfb3142310afb3a5c6b79185fd5a41b6a3d4a5a92f815e9b998` |

The hashes, JSON identity and parser behavior were independently replayed by data
and research reviewers. Transport metadata was recorded by the acquiring parent;
reviewers did not make independent network requests. The receipt does not certify
freshness, issuer truth, PIT availability or all concepts' period alignment.

At the producing revision, both parser outputs came from the unchanged
`app/data/fundamentals.py` (SHA-256
`0561c7ac315e6f12eca2ddf4faa6035f69d206f2f443dc2f5ee6f607993c89c6`).
The first revenue tag is
`RevenueFromContractWithCustomerExcludingAssessedTax`. Its selected FY2019 and
FY2020 rows have 91-day durations and revenue 64.040/64.698 billion USD.
History exposes both under annual fiscal labels. Latest FY2025 revenue is an
annual 364-day observation; this fixture establishes no latest-snapshot error.
Same-filing, same-end annual alternatives are 260.174/274.515 billion USD and
lack `frame`; requiring that field would not establish a repair.

A bounded sensitivity comparison changes only six parsed historical scalars,
using these literal same-filing alternatives. All other fields stay unchanged:

| FY | Accession | Annual start / end | Revenue USD | Net income USD | Diluted EPS |
|---|---|---|---:|---:|---:|
| 2019 | 0000320193-19-000119 | 2018-09-30 / 2019-09-28 | 260174000000 | 55256000000 | 11.89 |
| 2020 | 0000320193-20-000096 | 2019-09-29 / 2020-09-26 | 274515000000 | 57411000000 | 3.28 |

Give every history row and the current valuation an explicitly **synthetic**
price of 10. Actual parsed fields yield P/E and P/S percentiles zero and composite
score 0.9717424903153106. The constructed six-scalar intervention yields both
percentiles 1/7 and score 0.8765043950772154. Both retain seven observations,
empty flags and exactly the same other valuation fields. FCF-first growth
0.08998622735214545 and DCF value 117.96274231268941 are exactly unchanged.
This demonstrates mixed-period sensitivity, not an actual-price score, historical
backtest, split-adjustment correctness, screen admission or trading effect.

From the repository root, this read-only command checks the raw fixture and the
producing parser's historical selections (later parser fixes may intentionally
change the second assertion):

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import gzip
import hashlib
import json
from pathlib import Path
from app.data.fundamentals import parse_company_facts_history

path = Path("docs/evidence/FINDING-322/companyfacts.CIK0000320193.20261030.json.gz")
raw = gzip.decompress(path.read_bytes())
assert len(raw) == 3789099
assert hashlib.sha256(raw).hexdigest() == "73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43"
history = parse_company_facts_history(json.loads(raw), "AAPL")
assert [(y.fiscal_year, y.revenue) for y in history.years[:2]] == [(2019, 64040000000.0), (2020, 64698000000.0)]
print("Raw bytes and two historical parser selections verified")
PY
```

No runtime selector policy, threshold, generated record or historical experiment
is changed. FINDING-322 remains open for a separate ADR/TDD covering duration
versus instant concepts, non-December/fiscal-transition calendars, comparative
periods, restatements, ambiguous ties and source/PIT identity. One issuer is not
population calibration. See the finding for the full limits and verification.

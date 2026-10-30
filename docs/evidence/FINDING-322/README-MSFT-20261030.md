# Frozen Microsoft CompanyFacts evidence for FINDING-322

The complete, unmodified response body from the free official
[SEC Microsoft CompanyFacts endpoint](https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json)
is compressed with gzip, empty filename and modification time zero. Decompression
preserves every original byte and array order. This is a second chosen historical
capture, not population calibration or a current feed. Never refresh it in place;
the [original Apple capture](README.md) remains unchanged.

One prospectively bounded ordinary keyless request used the exact USER_AGENT in
backend/scripts/fundamental_sweep.py at producing revision
`078bfd4a89ab66f4b8c1768a4991ec80525e13eb`. TLS verification used the project
certificate bundle. No automatic redirect, retry, alternate header, auth, price
request, scorer or search was used. CIK 789019 was selected from the existing
read-only pool's MSFT identity and checked against the returned body.

| Receipt | Value |
|---|---|
| Request UTC | 2026-10-30T12:51:11.194170+00:00 |
| Completion UTC | 2026-10-30T12:51:11.602747+00:00 |
| HTTP status / content type | 200 / application/json |
| Response Date | Fri, 30 Oct 2026 12:51:11 GMT |
| Original and final URL | Official endpoint linked above |
| Decoded identity | CIK 789019; MICROSOFT CORPORATION; 562 us-gaap concepts |
| Raw length | 4,936,836 bytes |
| Raw SHA-256 | `464cc12cc4796c90a6a0c709eb4920788aa7d4d5eee8b44f2d11d7d44804ae37` |
| Gzip length | 317,923 bytes |
| Gzip SHA-256 | `ada0161dc22e170b2430905dc0414f9b7b6c8e2e7d06cfa01888155f960f54b4` |

Transport metadata is recorded by the acquiring parent. Offline review can verify
bytes, identity and actual parser behavior without independently authenticating
transport, freshness, source/issuer truth or PIT. Two selected filers establish
bounded exposure, not prevalence or a universal selector repair.

At the producing revision the unchanged modern first revenue tag selects
FY2018–2020 April 1–June 30 quarters under annual history labels. Revenue, net
income and diluted EPS all have literal same-filing annual alternatives beginning
prior July 1, with 365/365/366-day durations. Annual alternatives lack frame;
selected 2018/19 quarters also lack frame, so requiring it would not repair period
selection. Latest FY2026 revenue, income and EPS are annual; no wrong latest
snapshot is established. Full source tables and limits are in
[FINDING-322](../../findings/FINDING-322-fiscal-focus-filter-does-not-verify-fact-period.md).
No prices, new scores, financial substitutions, admission or historical experiment
claims are made. Runtime duration/instant/restatement/transition policy needs a
separate ADR/TDD; no generated record or parser is changed here.

Read-only reproduction from the repository root (a future parser repair may
intentionally change the producing-parser assertions):

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import gzip
import hashlib
import json
from datetime import date
from pathlib import Path
from app.data import fundamentals as f

packed = Path("docs/evidence/FINDING-322/companyfacts.CIK0000789019.20261030.json.gz").read_bytes()
assert len(packed) == 317923
assert hashlib.sha256(packed).hexdigest() == "ada0161dc22e170b2430905dc0414f9b7b6c8e2e7d06cfa01888155f960f54b4"
raw = gzip.decompress(packed)
assert len(raw) == 4936836
assert hashlib.sha256(raw).hexdigest() == "464cc12cc4796c90a6a0c709eb4920788aa7d4d5eee8b44f2d11d7d44804ae37"
payload = json.loads(raw)
assert payload["cik"] == 789019 and payload["entityName"] == "MICROSOFT CORPORATION"
gaap = payload["facts"]["us-gaap"]
assert len(gaap) == 562
quarter = {2018: (30085000000, 8873000000, 1.14),
           2019: (33717000000, 13187000000, 1.71),
           2020: (38033000000, 11202000000, 1.46)}
annual = {2018: (110360000000, 16571000000, 2.13),
          2019: (125843000000, 39240000000, 5.06),
          2020: (143015000000, 44281000000, 5.76)}
for column, (tags, unit) in enumerate(((f._REVENUE_TAGS, "USD"),
                                     (f._NET_INCOME_TAGS, "USD"),
                                     (f._EPS_TAGS, "USD/shares"))):
    tag = next(tag for tag in tags if f._annual_facts(gaap, (tag,), unit))
    selected = {row["fy"]: row for row in f._annual_facts(gaap, tags, unit)}
    for year in (2018, 2019, 2020):
        row = selected[year]
        assert row["start"] == f"{year}-04-01" and row["end"] == f"{year}-06-30"
        assert row["val"] == quarter[year][column]
        assert (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days + 1 == 91
        alternatives = [r for r in gaap[tag]["units"][unit]
                        if all(r.get(k) == row[k] for k in ("fy", "fp", "form", "filed", "accn", "end"))
                        and r.get("start") == f"{year-1}-07-01"]
        assert len(alternatives) == 1
        alternative = alternatives[0]
        assert alternative["val"] == annual[year][column] and "frame" not in alternative
        assert (date.fromisoformat(alternative["end"]) - date.fromisoformat(alternative["start"])).days + 1 == (366 if year == 2020 else 365)
history = f.parse_company_facts_history(payload, "MSFT")
assert len(history.years) == 9
assert [(y.fiscal_year, y.revenue, y.net_income, y.eps) for y in history.years[:3]] == [
    (year, *quarter[year]) for year in (2018, 2019, 2020)]
snapshot = f.parse_company_facts(payload, "MSFT")
assert snapshot.fiscal_year == 2026 and snapshot.revenue == 331839000000
assert snapshot.revenue_growth_yoy == 0.1778868679984666
print("Frozen bytes, nine quarterly selections/annual alternatives and latest annual snapshot verified")
PY
```

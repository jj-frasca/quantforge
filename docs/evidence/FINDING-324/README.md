# Frozen-source ROA timing witness for FINDING-324

This read-only replay reuses the immutable full CompanyFacts fixture from
[FINDING-322](../FINDING-322/README.md). It makes no network request and substitutes
no financial inputs. It checks literal dates and same-filing comparative balances
before computing exact ratios. The current parser/scorer is the producing
implementation at revision `5930d59db023b49cabf389f182c00149d213d0ee`;
a future explicitly adopted repair may change its assertions.

The constructed prefix ending FY2022 retains the original full-history citation,
including accession `0000320193-25-000079`. Its consumer result is an offline probe
of current code over older observations, not a contemporary FY2022 artifact, PIT
backtest, historical production run or reconstructed filing envelope. Keep parsed
`NetIncomeLoss` only conditionally as numerator: equivalence to the paper's income
before extraordinary items is not established. This verifies denominator timing
for these observations, not a complete paper-replication score or general policy.

Run from the repository root:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import gzip
import hashlib
import json
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path
from app.data.fundamentals import (
    FundamentalsHistory, _annual_facts, parse_company_facts_history,
)
from app.research.fundamentals.quality import piotroski_f_score, quality_score
from app.research.fundamentals.record import compute_fundamental_record

raw = gzip.decompress(Path(
    "docs/evidence/FINDING-322/companyfacts.CIK0000320193.20261030.json.gz"
).read_bytes())
assert hashlib.sha256(raw).hexdigest() == "73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43"
payload = json.loads(raw)
gaap = payload["facts"]["us-gaap"]
assets = {r["fy"]: r for r in _annual_facts(gaap, ("Assets",))}
income = {r["fy"]: r for r in _annual_facts(gaap, ("NetIncomeLoss",))}
assert [(assets[y]["end"], assets[y]["val"]) for y in (2020, 2021, 2022)] == [
    ("2020-09-26", 323888000000), ("2021-09-25", 351002000000),
    ("2022-09-24", 352755000000),
]
assert [(income[y]["start"], income[y]["end"], income[y]["val"])
        for y in (2021, 2022)] == [
    ("2020-09-27", "2021-09-25", 94680000000),
    ("2021-09-26", "2022-09-24", 99803000000),
]
assert all("start" not in assets[y] for y in (2020, 2021, 2022))
for y in (2021, 2022):
    row = income[y]
    assert all(row[k] == assets[y][k] for k in ("fy", "fp", "form", "filed", "accn"))
    assert assets[y]["end"] == row["end"]
    assert date.fromisoformat(assets[y-1]["end"]) + timedelta(days=1) == date.fromisoformat(row["start"])
    assert (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days + 1 == 364
    comparative = [r for r in gaap["Assets"]["units"]["USD"]
                   if all(r.get(k) == assets[y][k] for k in ("fy", "fp", "form", "filed", "accn"))
                   and r["end"] == assets[y-1]["end"]]
    assert len(comparative) == 1 and comparative[0]["val"] == assets[y-1]["val"]

history = parse_company_facts_history(payload, "AAPL")
prefix = FundamentalsHistory.model_validate({
    **history.model_dump(),
    "years": [y for y in history.years if y.fiscal_year <= 2022],
})
a, p, t = prefix.years[-3:]
assert [(y.net_income, y.total_assets) for y in (p, t)] == [
    (94680000000.0, 351002000000.0), (99803000000.0, 352755000000.0),
]
closing = (Fraction(p.net_income) / Fraction(p.total_assets),
           Fraction(t.net_income) / Fraction(t.total_assets))
beginning = (Fraction(p.net_income) / Fraction(a.total_assets),
             Fraction(t.net_income) / Fraction(p.total_assets))
assert closing == (Fraction(47340, 175501), Fraction(99803, 352755))
assert beginning == (Fraction(11835, 40486), Fraction(99803, 351002))
assert closing[1] > closing[0] and beginning[1] < beginning[0]
f = piotroski_f_score(prefix)
q = quality_score(prefix)
r = compute_fundamental_record(prefix)
assert f.delta_roa_positive and f.score == r.f_score == 8
assert q.score == r.quality_score == 0.6675842309900554
assert r.value_score is None and r.combined_score is None
assert prefix.accession_number == history.accession_number == "0000320193-25-000079"
print("Source continuity, exact trend reversal and offline consumer claims verified")
PY
```

No parser, scorer, numerator mapping, missing-balance policy, generated record,
threshold or cohort is changed. The latest FY2025 trend increases under both
scalings in this capture. Source authenticity, all-filer/run incidence, income
mapping, PIT availability and complete paper alignment remain open.

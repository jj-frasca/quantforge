# Offline score-vintage readiness census — W46 session21

This is exhaustive metadata accounting at pinned revision
`f30dda6987dff8ec8a705ec5ab8922de20d07d5c`, not an economic experiment.
`contract.md` was written before blob enumeration, after prior triage had already
seen the 14 commit count and earliest/latest dates. Independent research review
approved that scope before enumeration. No new architecture, source or study
policy is adopted, so no ADR or production-code change is needed.

`vintages.json` records every path-changing commit reachable from the pin,
original Git blob identity and SHA256, byte count, record/combined-score counts,
and duplicate-identity extra-row counts. Original blobs stay in Git; no generated
file is copied back or modified. A symbol duplicate is counted literally from
stored symbols; it is not an adjudicated identity collision or a new exclusion.
No rankings or score performance are computed.

Reproduce from repository root with full existing Git history (a shallow clone
may lack these objects). This reads Git objects and writes stdout only:

```sh
python3 - <<'PY'
import collections
import datetime
import hashlib
import json
import subprocess

revision = 'f30dda6987dff8ec8a705ec5ab8922de20d07d5c'
path = 'data/fundamentals_pool.json'
commits = subprocess.check_output(['git', 'log', '--reverse', '--format=%H', revision, '--', path], text=True).splitlines()
rows = []
for commit in commits:
    metadata = subprocess.check_output(['git', 'show', '-s', '--format=%aI%n%cI%n%s', commit], text=True).splitlines()
    raw = subprocess.check_output(['git', 'show', f'{commit}:{path}'])
    records = json.loads(raw)
    assert isinstance(records, list)
    symbols = collections.Counter(r['symbol'] for r in records)
    ciks = collections.Counter(r['cik'] for r in records)
    rows.append(dict(commit=commit, author_time=metadata[0], committer_time=metadata[1], subject=metadata[2], blob_oid=subprocess.check_output(['git', 'rev-parse', f'{commit}:{path}'], text=True).strip(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), records=len(records), combined_nonnull=sum(r['combined_score'] is not None for r in records), duplicate_symbol_extra_rows=sum(n-1 for n in symbols.values()), duplicate_cik_extra_rows=sum(n-1 for n in ciks.values())))
ceiling = datetime.date(2026, 11, 13)
first = min(datetime.datetime.fromisoformat(r['committer_time']).astimezone(datetime.timezone.utc).date() for r in rows)
span = (ceiling-first).days+1
result = dict(revision=revision, path=path, evaluation_date_ceiling=str(ceiling), enumeration='git log --reverse --format=%H REV -- data/fundamentals_pool.json', timestamp_qualification='Git metadata only; not remote publication or per-fact PIT proof', earliest_committer_date=str(first), n_revisions=len(rows), optimistic_calendar_date_rows=span, required_search_rows=252, required_holdout_rows=252, minimum_total_rows=504, optimistic_shortfall_rows=504-span, geometry_necessary_condition_met=span>=504, rows=rows)
print(json.dumps(result, indent=2, allow_nan=False))
PY
```

The date ceiling deliberately includes all of November13, even though this run
started near00:00 Pacific. Every calendar date is counted, including weekends
and holidays. This is an optimistic upper bound, not an exchange calendar,
count of actual return observations, or assertion that a vintage is one return.
Git timestamps are not independent publication evidence. The earliest August18
remote-publication receipt is retained under ADR417/FINDING351; this census does
not authenticate every intervening push or reconstruct filing-time availability.
Absent older objects outside this pinned reachable archive are outside scope.

The actual default geometry is `split_panel_holdout` in
`backend/app/research/cross_sectional/engine.py`: min_search_bars252 and
min_holdout_bars252. `search.py` calls it without overriding those floors;
`hunt.py` separately admits symbols only with504 prices. Merely having504 price
rows before the first published score would not supply504 causal score/price
rows. Repeating a static score over prepublication history remains conditional,
not PIT evidence. Meeting504 later would still not certify gate/MinTRL success.

No new economic trial or source request occurred. Existing selection accounting,
ADR418 fixed-unit 10bp entry+exit costs, EW/SPY/cash controls and February11 final
window remain unchanged. All gross/net economics and financial gates are NOT
MEASURED here. No frozen attempt root was used or created.

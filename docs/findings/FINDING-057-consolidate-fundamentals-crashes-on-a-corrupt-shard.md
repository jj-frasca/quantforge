# FINDING-057: A single corrupt shard crashes the whole fundamentals consolidation

- **Severity:** Medium
- **Status:** Resolved by ADR-129
- **Found:** 2026-09-24, autonomous session 104 (background audit of `backend/scripts/
  consolidate_fundamentals.py`, cold since 2026-08-18)
- **Affects:** `backend/scripts/consolidate_fundamentals.py` (ADR-029 Layer 3 consolidation)

## Finding

`consolidate_fundamentals.py`'s per-shard loop called `load_fundamentals_pool(shard_file)` for
every shard the fundamental sweep produced, with no error handling. `load_fundamentals_pool`
(`app/research/fundamentals/record.py`) raises on malformed content — `json.JSONDecodeError` for
truncated/invalid JSON, `pydantic.ValidationError` for a record that fails schema validation — it
only degrades gracefully for the "file absent" case.

`fundamental_sweep.py` writes each shard's output with a single non-atomic
`out_file.write_text(...)` inside a long-running (350-minute-timeout) cloud job. A shard process
killed mid-write, or interrupted by the runner, can leave a truncated/invalid JSON file behind;
`fundamental-sweep.yml`'s upload step uploads whatever bytes exist regardless. A single such shard
would raise an uncaught exception in `consolidate_fundamentals.py::main()`, crashing the entire
week's consolidation — losing every OTHER shard's good work, not just the corrupt one — and the
workflow's "commit fundamentals pool" step never runs.

This directly contradicts the resilience pattern `fundamental_sweep.py` itself documents and
practices for individual companies ("Per-symbol errors... are recorded and skipped so one bad name
never crashes the shard") — the same principle was never applied one level up, at the
shard-file-per-shard-job granularity that consolidation itself operates at. The gap was untested:
`load_fundamentals_pool`'s test coverage only exercised the "file absent" case, never malformed
content.

## Reproduction

```python
from pathlib import Path
from app.research.fundamentals.record import load_fundamentals_pool

path = Path("/tmp/bad_shard.json")
path.write_text('[{"symbol": "AAA", "cik": 1,')  # truncated, as a killed writer might leave
load_fundamentals_pool(path)  # raises json.JSONDecodeError, crashing consolidate_fundamentals.py
```

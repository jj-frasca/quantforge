# ADR-426: Serialize the cross-sectional pool compactly

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Autonomous session 306 under standing autonomy

## Context

`data/cross_sectional_pool.json` was written with `indent=2` and reached 102.9 MB after the
long-history (ADR-416) experiments embedded 11-18 MB `data_quality_reports` blocks. GitHub rejects
pushes of files over 100 MB, so the scheduled cross-sectional hunt (2026-11-08 run) failed at its
commit step and every future append would fail the same way.

## Decision

`JsonFileCrossSectionalStore.add` writes `separators=(",", ":")` with no indentation. Content is
byte-for-byte semantically identical (`json.loads` equality verified); the file shrinks to ~63 MB.
The existing file is rewritten once, losslessly. No experiment is dropped or altered.

## Alternatives considered

- Git LFS: costs money / new service; forbidden by the charter.
- Gzip or sharding the store: touches every reader (API, forward script, frozen-protocol scripts); larger blast radius.
- Pruning `data_quality_reports`: deletes record; forbidden.

## Consequences / limits

This is a stopgap with ~37 MB headroom (roughly 15 hunts at current report sizes). Sharding or
compressing the store is the durable fix if long-history experiments recur.
`published_quality_value_study.py` records a sha256 of the pool bytes at its run time; that recorded
value describes the earlier file and is not re-verified by any gate.

## Reversal

Restore `indent=2` in `store.py`; the file stays valid either way.

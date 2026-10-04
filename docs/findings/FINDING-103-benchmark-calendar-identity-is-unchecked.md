# FINDING-103: Benchmark calendar identity is unchecked

- **Date:** 2026-10-04
- **Severity:** Medium — malformed observation identity can distort relative risk
- **Status:** Resolved by ADR-172

## Evidence

The public comparator accepts repeated dates as distinct observations. For dates Jan 1, Jan 3,
Jan 2, Jan 4 with strategy returns -20%, +25%, -20%, +25% and a flat benchmark, it reports relative
drawdown -20%. Chronological ordering places both losses together and yields -36%. The comparator
does not establish either input's unique chronological identity before inner alignment.

## Impact and limits

An unordered or duplicated direct caller can publish misleading relative risk or overweight repeated
observations. Normal checked datasets reject such bar identity upstream; no committed experiment or
production price series is alleged to be malformed. Valid partial overlaps are an intentional
contract under ADR-013 and must remain supported.

## Correction

ADR-172 rejects nonunique or nonascending input indexes before alignment. It preserves generic and
naive ordered indexes, valid partial overlaps, all metric formulas, and API fail-soft behavior.

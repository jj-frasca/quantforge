# ADR-146: Capture the raw numeric SIC code alongside its description

- **Status**: Accepted
- **Date**: 2026-09-28
- **Deciders**: Interactive session (Joe present, delegated: "find out how to make me money using
  these advanced strategies and whatever research you want to do")
- **Acts on**: ADR-095 (SIC classification in the fundamental sweep)
- **Relates to**: ADR-094 (ruled out history length as the driver of the 7,400-vs-9,247-bar cohort
  walk-forward-excess gap; named sector mix, size, and survivorship as the unmeasured candidates)

## Context

ADR-095 shipped `sic_description` (e.g. `"Real Estate Investment Trusts"`) specifically to let a
future session test whether sector mix explains the composition gap ADR-094 left open. That
coverage now exists: `data/fundamentals_pool.json` carries `sic_description` on 4,190 of 4,244 rows
(98.7%), and joining it against the 7,400-bar and 9,247-bar null-calibration cohorts (`n=91` /
`n=276`, `pool_report.history_coverage`'s own bucketing at `HISTORY_TOLERANCE`) gives 58 and 227
matched symbols respectively — the first time this join has ever been possible.

A first look at those two distributions (this session, description strings only) is suggestive:
Real Estate Investment Trusts are the single largest category in the 7,400-bar cohort at 8/58
(13.8%), more than 2.5x the next-largest category, where the 9,247-bar cohort's largest category
(Electric & Other Services Combined, 9/227) is only 4.0% — no dominant sector. **This is reported
here as a directional observation only, not a statistical result** — see the "What this ADR does
NOT do" section below for why it must not be read as confirming or refuting ADR-094's open
question.

The problem: `sic_description` is SEC EDGAR's free-text industry label — hundreds of distinct
strings across the pool (a `Counter` over the 285 matched symbols above already shows dozens of
singleton categories), too granular for a chi-square-shaped test without an external, non-invented
bucketing scheme. **The standard SEC Standard Industrial Classification is itself a numeric
hierarchy** (4-digit code -> 2-digit major group -> one of ten single-letter divisions, e.g. 3571
Electronic Computers -> major group 35 -> Division D, Manufacturing) with published, external
division boundaries this project did not design and cannot be accused of having fit to the pattern
just observed. `fetch_sic`'s own test fixture already carries the raw code
(`test_edgar_source.py::_submission`, `"sic": "3571"`) and the live submissions endpoint returns it
in the exact same JSON payload `sicDescription` is already parsed from (verified in ADR-095's own
research) — capturing it costs no additional network call, only using more of a response already
being fetched.

## Decision

**Add the raw `sic` code to the same fetch, record, and sweep path `sic_description` already
travels — an additive field on an existing pipeline, not a new one.**

1. `app/data/sources/edgar.py`: `fetch_sic` now returns a `SicClassification(code: str | None,
   description: str | None)` frozen value object instead of a bare `str | None`, parsing both `sic`
   and `sicDescription` from the one submissions response it already fetches. `code` is the raw
   string from EDGAR (e.g. `"3571"`) — not parsed into an int or mapped to a division here; that
   mapping is future analysis code's job, not the data-capture layer's.
2. `app/research/fundamentals/record.py`: `FundamentalRecord` gains `sic_code: str | None = None`,
   parallel to the existing `sic_description` field. `compute_fundamental_record` gains a matching
   `sic_code` parameter, attached as-is (no lookup, no division mapping — pure, network-free,
   consistent with the module's existing boundary).
3. `scripts/fundamental_sweep.py`: the `_sic_description` helper becomes `_sic_classification`,
   returns the whole `SicClassification`, and both fields flow into
   `compute_fundamental_record`. No second EDGAR call — same one-call-per-symbol budget ADR-095
   already established.
4. **No backfill, no local write, no SIC-to-division mapping shipped in this ADR.**
   `data/fundamentals_pool.json` is cloud-workflow-written only (ADR-030); `sic_code` populates the
   same way `sic_description` did, on the sweep's normal multi-week cadence. A future session that
   wants to run the actual sector-composition test against ADR-094's open question should wait for
   sufficient `sic_code` coverage on the two cohorts, then write the division mapping and the test
   as its own ADR — this one only removes the data gap blocking it.

## What this ADR does NOT do

- **It does not run, or claim to run, the ADR-094 composition test.** The description-level
  observation above is reported as a lead worth someone's future attention, explicitly NOT as a
  hypothesis test: the categories were inspected before any bucketing scheme was chosen, so any
  grouping designed now would be shaped by having already seen which one produces a bigger gap —
  exactly the kind of post-hoc, unregistered look this project's own discipline exists to prevent
  (ADR-063's and ADR-070's meta-lesson: state the test before you can see its answer). The correct
  fix is not to bucket the free-text descriptions around what was already seen; it is to wait for
  the numeric code this ADR now captures and apply the SIC division boundaries the government
  defined decades before this project's cohorts existed.
- **It does not gate, weight, or filter anything in the search or the gate.** Purely additive
  metadata, identical in kind to ADR-095's own field.
- **It does not backfill existing rows.** Coverage builds at the sweep's own pace; forcing it would
  make this session a second writer of a cloud-workflow-owned file (ADR-030).

## Alternatives considered

- **Design the SIC-to-division bucketing now, using only `sic_description` strings, and run the
  test today.** Rejected for the reason above: this session already looked at both distributions,
  so any bucketing scheme it invents now cannot be trusted not to have been shaped by that look.
  Waiting for the numeric code and using the SIC division scheme's own published boundaries removes
  that discretion entirely.
- **A yfinance sector lookup for just the 285 matched symbols, today, bypassing the sweep.**
  Rejected for the same reason ADR-095 rejected it: a one-off local pull does not persist for any
  future session, and this project's system-of-record for company metadata is the sweep-owned pool
  (ADR-029), not an ad hoc local join.
- **Parse `sic` into an `int` on the record.** Rejected: EDGAR pads/formats it as a 4-character
  string and every consumer so far (division lookup) wants string prefix matching (`code[:2]`), not
  arithmetic; storing it as EDGAR returns it avoids inventing a normalization this ADR doesn't need.

## Consequences

- `data/fundamentals_pool.json` rows gain `sic_code` as the sweep revisits each company, same
  cadence as every prior additive field.
- Unblocks, but does not itself perform, the actual ADR-094-composition test once coverage is
  sufficient on the 7,400-bar and 9,247-bar cohorts specifically (58/91 and 227/276 matched today
  on description alone; code coverage starts at zero and follows the same weekly cadence).
- No change to any gate, threshold, or production search path.

## How to reverse

Remove `sic_code` from `FundamentalRecord`, the parameter from `compute_fundamental_record`, revert
`fetch_sic`'s return type to bare `str | None`, and the sweep's call site. Existing pool rows keep
working either way — `sic_code` defaults to `None` and pydantic ignores/drops unknown keys
symmetrically on load.

## Measured

Not applicable — this ADR ships capture capability. The description-level sector-concentration
observation in Context is recorded as a directional lead for a future session's pre-registered test,
not as this ADR's own measurement.

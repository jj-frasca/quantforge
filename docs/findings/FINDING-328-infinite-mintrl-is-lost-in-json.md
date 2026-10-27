# FINDING-328: Intentional infinite MinTRL is lost in JSON

- **Status:** Corrected for validated GateResult JSON under ADR-386
- **Date:** 2026-10-27
- **Producing revision:** 5e2aec1b
- **Affected:** GateResult JSON and its nested experiment/calibration publication

## Evidence

ADR-015/160 deliberately permit required_track_record_years=positive infinity for
non-positive observed Sharpe. GateResult.model_dump_json instead writes null for
that value; GateResult.model_validate_json then rejects the required float. The
same loss occurs inside ordinary Experiment.best_gate_result and a validated
NullCalibration symbol diagnostic's calibration verdict. Independent data and
research reviewers reproduced these direct/nested failures without searches.

A parent deterministic flat 3,000-bar one-SMA/refine=True mechanics control through
the unmodified calibrate_gate searches one symbol, graduates none and produces
the intentional infinite requirement. Its ordinary JSON output has null and the
authoritative calibration reload rejects that nested float. This is a unit
mechanics control, not a statistical null-cohort measurement or a new source draw.

Official null/power/horizon drivers and consolidators use model_dump_json, so they
can write this loss. The experiment stores instead use model_dump(mode="json")
plus Python json.dumps: that emits nonstandard bare Infinity and permissive Python
loaders round-trip it. Not every writer loses the value. Strict JSON encoding
refuses that route, including JSON response construction from an encoded graph.

The independent bounded scan of 617 generated research/null/power JSON files
found 3,967 required-history leaves, all finite, and 3,967 complete GateResult
objects validating. Source hashes stayed exact. This establishes no affected
historical generated row, workflow or calibration; no real company/graduate/
trading effect is claimed. Historical lost null values are not recoverable merely
from this serializer and must never be silently reinterpreted as infinity.

## Correction and limits

ADR-386 uses a JSON-only field serializer on required_track_record_years. Only
positive infinity becomes literal string "Infinity"; finite values and native
Python dumps remain unchanged. The existing float reader already accepts that
string and reconstructs positive infinity, so no decoder or null repair is added.
Generic ser_json_inf_nan="strings" leaves model_dump(mode="json") as float infinity
and therefore misses the current store/strict-JSON path.

This changes the serialization schema to number-or-literal-"Infinity" for this
leaf. External consumers must handle the tag. The null/power read-only APIs expose
the nested leaf; the current frontend schema omits/strips it. Thresholds, MinTRL
math, nonpositive-Sharpe impossibility, gate verdicts and v14 identity stay.
Construction still rejects NaN/negative infinity; unchecked invalid copies and
unrelated nonfinite fields receive no new validity guarantee.

## Verification

The inherited pre-code receipt records 14 genuine failures and 10 passing controls:
seven null-leaf assertions, five strict-JSON infinity errors and two bare-Infinity
store parsing errors. After the serializer, all 24 new tests pass, including the
official deterministic flat calibration mechanics control, actual null API/schema,
both pool writers, invalid-input controls and Hypothesis finite round trips.

Session8 independently resumed the seven paths before fetching/rebasing. The
frozen baseline replay matches 45 complete finite artifact JSON/Python claims,
five native infinite graphs and the whole gate AST outside serializer/imports.
Independent research33 and data138 focused synthetic tests pass; reviewers approve.
Additional data controls confirm the actual power API and five legacy bare-Infinity
round trips. Fresh full foreground gate and exact post-push CI are recorded in the
session ledger. No generated record is edited.

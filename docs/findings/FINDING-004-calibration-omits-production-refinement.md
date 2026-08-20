# FINDING-004: Calibration omits production's adaptive refinement pass

- **Severity:** Critical (methodology calibration measures a different selector)
- **Status:** Fixed by ADR-047
- **Affected:** ADR-036/037/041/042/044/045, null and power calibration

## Finding

Daily discovery and the main universe hunt call `run_universe_hunt(..., refine=True)`. Null and
power calibration call `run_search` without `refine`, whose default is false. Calibration therefore
measures a coarse-only selector while production performs a data-dependent second search around the
coarse winner before applying the gate.

ADR-036 describes calibration as the **unmodified search + gate**, and ADR-041 interprets power as
the production pipeline's ability to detect an edge. Those claims require the same adaptive search
procedure. Refinement adds hypotheses selected because the coarse data looked promising; omitting
that adaptive step from the null is particularly unsafe because it is another opportunity to fit
noise.

ADR-044's `search_config_version` does not expose the mismatch. It fingerprints gate config,
`n_per_param`, strategy order, and coarse grids, but not `refine` or `refine_span`. Coarse-only and
coarse-to-fine measurements can share an identity.

## Evidence

- `backend/scripts/shard_hunt.py` and `backend/scripts/run_hunt.py` pass `refine=True`.
- `calibrate_gate` and `measure_power` call `run_search` without `refine` or `refine_span`.
- `calibration_search_version` omits both fields.
- ADR-046 now correctly counts every refined config in DSR/MinTRL, making omission of the entire
  pass from calibration explicit rather than hidden behind the prior `+1` family-summary count.

## Impact

The published 1% Type-I error and power/capture tables describe the old coarse-only procedure at
their recorded catalog, not production discovery. They are not evidence that production refinement
is leaky, but they cannot be cited as measurements of that refined selector. The accounting-method
fingerprint added by ADR-046 already makes a new run necessary; refinement parity must land before
that compute is spent.

## Required behavior

- Null and power calibration must use production's default refinement policy.
- `refine` and `refine_span` must be explicit calibration inputs and part of search identity.
- Calibration artifacts must expose the policy rather than only an opaque hash.
- Coarse-only calibration remains possible only as an explicit non-production diagnostic.

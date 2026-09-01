# FINDING-016: Null diagnostics lose per-symbol pairing in parallel arrays

- **Severity:** High — methodology attribution and drift-controlled null comparison
- **Found:** 2026-09-01 by Codex hostile review of ADR-068 / ADR-078 calibration artifacts
- **Status:** Resolved by ADR-080
- **Affected:** `backend/app/research/lab/calibration.py`,
  `backend/app/research/lab/pool_report.py`

## Finding

`NullCalibration` stores walk-forward OOS, walk-forward hold, purged-CV OOS, and purged-CV hold
Sharpes as four independent lists. `calibrate_gate` builds each list with its own nullable filter,
and `merge_calibrations` concatenates each list independently across shards. The artifact retains no
symbol identity for any entry.

`compare_with_null` refuses an excess row when the OOS and hold list lengths differ. Equal lengths
do not prove pairing: complementary missingness can remove different symbols from the two lists, or
from different shards, while leaving the same aggregate count. Zipping those arrays then subtracts
one symbol's benchmark from another symbol's finalist and presents the result as paired excess.

The 2026-09-01 7,400-bar artifacts are not presently affected: all four diagnostic lists contain
exactly 200 entries for 200 searched symbols. The defect is latent in the schema and merge contract,
not evidence that the published values are numerically wrong.

## Impact

An artifact with partial diagnostic missingness can produce a formally comparable, tightly bounded
drift-controlled null distribution whose observations were never paired. Because the excess band is
roughly an order of magnitude tighter than the raw band, silent cross-symbol subtraction can change
the project's central real-versus-null reading without changing a gate threshold or raising an
error.

## Required correction

New calibrations must persist one diagnostic record per searched symbol, carrying the symbol and
all nullable OOS/hold measurements together. Shard merge must preserve and validate those records.
The report must derive excess only from explicitly paired fields. Legacy arrays may be paired by
index only when both arrays are complete for all `n_symbols`; partial legacy arrays are useful for
raw distributions but cannot establish a paired excess.

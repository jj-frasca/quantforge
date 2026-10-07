# FINDING-114: Missing returns inflate PSR sample count

- **Date:** 2026-10-07
- **Severity:** High — missing rows can manufacture probability evidence
- **Status:** Resolved by ADR-182

## Evidence

`return_moments` uses pandas std/skew/kurt, which skip NaNs, but records n_returns as len(series).
Five observations `[-0.02, 0.01, 0.025, 0.04, 0.03]` have skew approximately -1.182883 and raw
kurtosis 4.212440. Appending 100 NaNs leaves those moments unchanged but increases n_returns
from five to 105. Independent research-expert reproduction with fixed per-period Sharpe 0.2 and
benchmark zero increases PSR from approximately 0.638752 to 0.964913 solely through missing padding.
Complex and boolean inputs also produce real moment records rather than enforcing the input domain.

## Correction and limits

ADR-182 requires complete finite real nonboolean numeric input before short/constant shortcuts.
Missing observations are rejected rather than dropped or counted. Native valid moment arithmetic,
raw kurtosis and sample length remain unchanged. Finite short/constant histories remain unmeasured;
signed observations including <=-1 remain valid distribution inputs. Checked engine paths already
produce complete returns, so this is not a claim that committed probabilities contain this defect.
No margin gate, probability estimator, threshold, generated data or calibration identity changes.

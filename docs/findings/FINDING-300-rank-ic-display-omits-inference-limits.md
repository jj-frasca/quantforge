# FINDING-300: Rank IC display omits selected-sample and t-statistic limits

- **Date:** 2026-10-24
- **Review:** Codex autonomous session 29, ISO 2026-W43
- **Status:** Resolved by ADR-360 (presentation scope only)
- **Area:** Cross-sectional dashboard interpretation, ADR-035

## Finding

`CrossSectionalPanel` describes rank IC as saying whether the ranking carried
information and labels its statistic simply "IC t-stat". It does not surface the
independent-period assumption already stated in `ICSummary`, or the search-sample
family-finalist selection visible in the current producer.

`run_cross_sectional_search` computes config Sharpes on `in_sample`, chooses
`best_i = int(np.argmax(sharpes))`, builds that config's signal on `in_sample`,
and records `summarize_ic(rank_ic(finalist_signal, in_sample))`. `summarize_ic`
reports `mean / max(std, 1e-12) * sqrt(n)` without serial-dependence or
search-selection adjustment. IC does not itself select or gate candidates.
ADR-035's inference that this removes selection bias is unsupported: the
reported configuration was selected using outcomes on the same sample.

## Deterministic evidence and limits

The original helper gives exactly the same complete summary for 100 observations
arranged as `[0.125, 0.375] * 50` and `[0.125] * 50 + [0.375] * 50`:
mean 0.25, sample std 0.1256297269074015, IR 1.98997487421324,
t-stat 19.8997487421324, hit rate 1.0 and count 100. Their empirical lag-1
correlations differ (approximately -1 and 0.98). This establishes that the
reported statistic does not use chronology, not that either synthetic sequence
is a market process or that any real t-stat has a measured error. Reproduction:
`/tmp/qf-w43-s29-ic-chronology.json`. Independent research and frontend source
reviews confirm the bounded interpretation.

No observed market bias magnitude/direction, invalid graduate, p-value or
historical provenance claim follows. No generated/frozen evidence was modified,
and no old cohort was rerun or replaced.

## Resolution and verification

ADR-360 prescribes visible scope/assumption copy and a qualified t-stat heading,
with tests first and unchanged numeric cells, missing values and server verdicts.
No estimator, schema, gate, threshold, search identity or accounting change.
Five new RTL cases genuinely failed against the original panel before the patch;
all 24 panel tests then passed, independently reproduced by the frontend reviewer.
Independent research and frontend final reviews approved the bounded claims.
The whole component remains byte-identical except the IC lede and single header;
backend search/IC and frontend schema bytes remain unchanged. Fresh foreground
`make check-all PYTEST_WORKERS=2` passed: 14,537 backend tests and 736 frontend
tests, with lint, format and type checks green. Local gate receipt:
`/tmp/qf-w43-s29-check360.log`; preservation receipt:
`/tmp/qf-w43-s29-ic-preservation.json`. This resolves disclosure, leaving
dependence-aware inference and independently measured IC outside this decision.

# FINDING-330: Nonfinite Piotroski operands become finite quality points

- **Status:** Corrected within active Piotroski input consumption under ADR-389
- **Date:** 2026-10-27
- **Producing revision:** e34b11a3
- **Affected:** piotroski_f_score, quality_score and compute_fundamental_record

## Evidence

With two adjacent ordinary annual rows, revenue/assets 100 and net income 10, latest
operating_cash_flow=positive infinity awards both cfo_positive and accruals_quality.
The result is F-score 3 and finite quality 1/3, accepted by FundamentalRecord. Missing
or zero cash flow gives F-score 1 and quality 1/9. Finite cash flow 20 intentionally
gives the same flags as infinity; this comparison establishes no economic truth
for the invalid value. NaN/negative infinity instead erase to false and the finite
base score. The parent six-case witness and independent data/research controls
agree; their fixtures with net income 0 have the corresponding F-score 2 vs 0.

The unmodified CompanyFacts history parser also accepts a synthetic raw string
"Infinity" in the latest operating cash flow fact and converts it to numeric
infinity. In the existing full synthetic fixture, compute_fundamental_record then
accepts F-score 8/quality 0.7353931471578531 with no flags. This is accepted-domain
parser evidence, not an SEC response, valid filing, real company or vendor-incidence
claim. No provider, search, calibration cohort or external service was used.

Output finiteness cannot recover raw numeric invalidity after comparisons form
booleans. ADR-155's finite pool fields therefore accept the result. ADR-384/385
protect only safety components/operands and explicitly exclude F-score/OCF.
ADR-116/117 fiscal adjacency, ADR-380 derived gross-profit fallback and F324's
same-year ROA proxy address different scopes. No historical affected row, false
actual graduate, trading effect or measured calibration-rate change is established.

## Correction and limits

ADR-389 preflights present operands locally after the existing fewer-than-two-row
zero return and fiscal adjacency decision, before ratios or comparisons. Always
check the eight latest fields the current function reads. Only with adjacent
labels, also check latest diluted shares and the eight consumed prior fields.
Prior OCF, older rows and gap-disabled share/prior operands remain ignored.

Missing peers, zero denominators or another failed signal cannot hide present
invalid active evidence. A stable named plain ValueError propagates; no invalid
value becomes missingness or a zero point. Availability becomes stricter, and
F-score refusal can precede existing safety refusal because quality computes it
first. Sweep scoring occurs outside acquisition recovery and may abort before
shard output. No new skip, fallback or partial-output policy is introduced.

None and all finite native formulas, score/ranking thresholds, same-year ROA,
year selection, global Annual/history schemas and accounting-v14 remain. This
raw-operand guard does not certify finite computed ratios: finite cash flow 1e308
and assets 1e-308 still overflow their ratio under existing arithmetic. That is a
separate limitation, not asserted here as an incorrect exact-real inequality.
Short-history zero behavior, period/PIT provenance, unchecked source truth and
historical erased evidence are not repaired.

## Verification

Written scratch findings and independent prospective scope reviews precede the
permanent finding/ADR and tests/source. The authoritative pre-code run has 181
genuine failures and 24 passing controls: 158 missing ValueError and 23 intentional
earlier-error regex mismatches. No import, collection or fixture errors count.
The 205 new tests then pass, with 448 parent focused, 222 research focused and 381
data focused synthetic tests green. Both final independent reviewers approve.

The frozen parent baseline contains 291 histories/873 complete FScore, QualityScore
and FundamentalRecord JSON/Python claims plus the whole quality AST. Parent and
reviewers replay these exactly outside the explicit preflight block. Tests cover
all 17 active role/field operands, direct/quality/record consumers, the unmodified
synthetic parser, missing/zero/error precedence, ignored short/gap/older inputs,
Hypothesis finite point arithmetic and preserved finite-derived overflow. The
actual sweep is fully mocked to verify refusal before output or the next company;
no provider/price service is called. Full foreground gate and exact post-push CI
receipts are recorded in the session ledger. No generated data is edited.

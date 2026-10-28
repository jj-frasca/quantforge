# FINDING-331: Finite Piotroski operands can erase ratio ordering

- **Status:** Open; ADR-390 adopts refusal for nonfinite derived ratios only
- **Date:** 2026-10-27
- **Producing revision:** 97229643
- **Affected:** piotroski_f_score, quality_score, compute_fundamental_record

## Evidence

ADR-389 validates raw active operands but preserves native binary64 division.
With latest assets 1e-308, net income 1e308 and operating cash flow 1.5e308,
ROA and CFO/assets both overflow to positive infinity. Their strict accrual
comparison is False. Fraction.from_float applied independently to each accepted
operand proves CFO/assets > NI/assets. Using a prior row with assets1, revenue1
and NI0, and latest revenue1 with other optional inputs absent, the producer
accepts F-score4 and quality4/9 in a FundamentalRecord. Changing only that accrual
point would give5; that conditional comparison is not a full paper replication.

Two finite-result examples show why finiteness alone cannot close the finding:

- Assets1e308, NI1e-308 and CFO2e-308 give both ratios0. With the same prior row,
  the native F-score1 loses three exact-float positive points: ROA, ROA improvement
  and accrual quality. The corresponding conditional score is4.
- Assets3, NI7 and CFO7.000000000000001 give both native ratios
  2.3333333333333335, although the exact accepted CFO operand is greater. The
  accrual point is False. This is ordinary finite rounding, not just an extreme
  overflow or underflow domain.

Independent research reproduction confirms all three with exact Fraction
comparisons and actual producer outputs. These are constructed accepted-domain
histories, not SEC facts, vendor incidence or historical affected records.
Finite durable score validation cannot reconstruct ratio operands after their
comparisons have become booleans. No affected graduate, trading effect or changed
calibration rate is established. No provider, search or cohort was executed.
F324's same-year ROA proxy and F322's physical-period/PIT limits remain separate.

## Partial correction and limits

ADR-390 requires each present computed Piotroski ratio finite before booleans.
It refuses overflow rather than assigning missingness, a zero point or an exact
replacement score. All eleven ratios actually computed are checked, including
latest ratios whose trend comparison has no adjacent prior. Prior ratios remain
None when adjacency disables them. Existing raw guards still precede division.
A named plain ValueError propagates through quality/record and can abort sweep
scoring before shard output; no fallback or skip policy is introduced.

Finite underflow, ordinary rounding ties and other finite comparison projection
errors remain OPEN. This guard does not certify exact-real inequalities or paper
replication. Finite native arithmetic, None/zero-denominator behavior, score
thresholds, history selection, shared _ratio, schemas, generated records and
accounting-v14 remain unchanged. No historical inputs or scores are repaired.

## Verification

Prospective written scratch evidence precedes permanent finding/ADR and source.
The pre-source baseline captures288 histories/864 complete FScore, QualityScore
and FundamentalRecord JSON/Python claims plus the entire quality module AST.
The actual pre-code run has72 failures and31 passing controls:68 missing refusals
and4 error-precedence mismatches where later safety validation previously raised.
No import, collection or fixture failures count. After the16-line production
guard,103 new tests and the retained overflow fixture pass. A postgreen extension
of the existing fully mocked sweep test adds one derived-refusal control; no
additional pre-code claim is made for it. Parent focused326 and independent
research364 synthetic tests pass; final independent review approves. Both parent
and reviewer replay the864 complete claims and whole AST outside the exact guard
unchanged. Tests cover all11 signed-overflow ratios through3 consumers, exact
Fraction witnesses, gap/missing/zero/error precedence and Hypothesis native
finite comparisons. Full foreground gate and exact post-push CI receipts are
recorded in the session ledger. No generated record is authored.

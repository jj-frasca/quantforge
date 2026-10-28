# FINDING-331: Finite Piotroski operands can erase ratio ordering

- **Status:** Partially addressed by ADR-390/395/397: nonfinite, zero-underflow and inconsistent accepted-operand pair predicates refuse; broader scalar/source limitations remain
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

ADR-390 alone leaves finite underflow, ordinary rounding ties and other finite
comparison projection errors OPEN. This guard does not certify exact-real inequalities or paper
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

## Zero-underflow refusal (ADR-395)

At the pre-395 c93aecab producer, independent research and data reproductions
again accept the finite-underflow history above through FScore, QualityScore and
FundamentalRecord:1,1/9,1/9. Fraction arithmetic on the actual accepted floats
proves CFO/assets > NI/assets > 0. All four numerator/denominator sign pairs
also produce a signed native zero from a nonzero exact quotient. This is
constructed direct-call evidence, not observed vendor data or historical incidence.

ADR-395 adds an ordered local check after the entire existing eleven-ratio
finiteness loop. A present zero ratio with two present nonzero original operands
refuses with a named plain ValueError before score booleans. True signed-zero
numerators remain valid; None/zero denominators, short histories and disabled
prior ratios retain their availability rules. Latest ratios remain checked
across fiscal gaps. Completing the old finite loop first preserves its precedence
when an early zero-underflow ratio coexists with a later overflow.

This refuses lost evidence rather than recovering exact comparisons or assigning
a missing/zero score. Existing quality/record propagation can abort sweep output;
no skip or fallback is added. Nonzero subnormal projection errors, ordinary
rounding ties and other finite comparison limits remain OPEN. F324's same-year
ROA proxy, F322's period/PIT limits and all thresholds remain separate. No source,
search/cohort measurement or generated-record repair is performed.

The actual pre-code run has149 failures and90 passing controls:147 missing
refusals and2 intended earlier-safety error-precedence mismatches. No collection,
import or fixture errors count. The23-line guard passes239 new tests and565
parent focused tests. Independent research and data each pass603 synthetic tests
including record regressions and approve the correction. Both replay all
288 histories/864 complete valid producer claims and the whole module AST outside
the exact guard unchanged. Coverage includes eleven ratios, four operand-sign
pairs, all three consumers, exact Fraction/property witnesses and a fully mocked
real sweep. The first full gate exposes a second existing cash-flow property at
cash5e-324/assets2000. Its generator remains unchanged, with explicit signed
min-subnormal examples and refusal in the new domain. Both existing properties
and projection examples remain, with their native assertions elsewhere. Full foreground gates
and exact post-push CI receipts are recorded separately in the session ledger.

## Exact accepted-operand predicate refusal (ADR-397)

Prospective independent research certifies24 constructed canonical-float histories:
six pair components, ordinary/nonzero-subnormal collisions, both denominator
signs. Ordinary7 and nextafter(7,+inf) divided by3 tie at2.3333333333333335;
1 and nextafter(1,+inf) divided by1.7e308 tie at5.88235294117647e-309.
Each actual producer accepts a False native strict signal where exact Fraction
arithmetic on accepted operands proves True. Negating both numerator and
denominator preserves each witness. These are direct-call constructions, not
provider incidence or historical affected records. An attempted1/1e308 witness
did not collide and supplies no positive evidence.

ADR-397 checks the six available ratio-pair predicates after all existing raw,
nonfinite and zero-underflow guards. A mismatch refuses with a named plain
ValueError; native booleans and scores are never replaced. Exact conversion
normalizes Integral values to Pythonint, otherwise uses the scalar's native
as_integer_ratio protocol, validating two nonboolean Integral members and nonzero
denominator before Fraction construction. No float projection or floating cross
products are used. Standard float/NumPy/Fraction/Decimal exactness is supported
where the existing native arithmetic already succeeds; arbitrary custom protocol
truthfulness is assumed, not certified. A missing/malformed/unsupported exact
protocol on an active pair adds a named precision refusal, an explicit additional
availability restriction. Normal validated schema operands are already floats;
this cannot recover original decimal/vendor precision discarded upstream.

Missing pairs and gap-disabled prior comparisons remain inactive. Latest accrual
remains active across gaps. Negative denominators retain their economics; exact
rational operations account for their sign. Comparison order follows existing
signal order, after the entire old guard sequence. Refusal propagates through
quality/record and can abort sweep output, with no fallback or historical repair.
The five ratio trends and accrual are checked; raw CFO/no-dilution, other scorers,
arbitrary custom arithmetic, F324's ROA proxy and F322's source/PIT truth remain
separate. No generated evidence, threshold, fingerprint, cohort or v14 change.

The pre-source baseline captures288 histories/864 complete producer claims and
whole-module AST. The corrected actual pre-code run has94 failures and151 passing
controls:92 missing refusals and2 intended error-precedence mismatches. An earlier
run included18 record-fixture errors; those are excluded from methodology RED.
The267 new tests include245 exercised before implementation and22 postgreen
reverse-direction/protocol-exception extensions, without additional RED claims.
Both retained cash-flow properties keep their generation domains and native
assertions outside the new precisely identified refusal domain. The inherited
parent focused suite passes870 tests; fresh independent research passes631 and
data passes870 synthetic tests, with both final reviews approving. Parent and
both reviewers reproduce all864 complete baseline claims and whole-module AST
outside the frozen exact additions unchanged. Full foreground gate and exact
post-push CI receipts are recorded separately in the session ledger.

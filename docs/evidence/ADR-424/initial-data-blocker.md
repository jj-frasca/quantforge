# ADR424 independent nonimplementing final data review — pre-correction

Decision: BLOCK release on the strict-screen tie defect identified by independent
research. Source, preflight, durability and retention paths otherwise conform.
This receipt describes original frozen moduleSHA
 d9a6a2d5e7b75ce89469a7bce7d6a4da873db1482404fad44b294c74cf9058fb,
CLI54e8721c377c0f275218dbf472ab5b6c1915e0e2d88490cc793f2a2d5bdb0798,
tests2f608c77fa50933dd03c6fe70425a1feaef551b0aeb8ca143a7a8f9c996f428b.
It is not final approval of any later correction.

Independent runtime checks:
- All35 new focused tests passed in21.03s; log
  /tmp/qf-w45-s10-424-independent-data-tests.log.
- All694 protected generated/evidence/old417 source/test path hashes remain exact.
- Three frozen implementation/test hashes match the builder's release candidate.
- Own separate fsync oracle confirmed regular START file fsync plus both root and
  root-parent directory fsync precede provider construction. Intentional provider
  construction interruption leaves START and no result, and a second invocation
  refuses the occupied root without provider access.
- Own separate full64-label mixed-source fixture retained exactly the original
  failed DQ report, including UUID/time/error details, before UNEVALUABLE. It made
  only one source call, retained the canonical source payload/hash, wrote no
  passing dataset evidence and exposed no account or screen result.
  Script/log: /tmp/qf-w45-s10-424-independent-data-oracle.{py,log}.

Text inspection confirms original DQ/passing dataset evidence precede exact
calendar refusal; storage writes are outside source-error catches; deadline
checks follow durable START and attempt markers before provider/request effects.
Portable pinned identities, actual module/lock/distribution/Decimal/default
metadata and original own-seal publication hashes are preserved. The CLI has no
root/window/input/vendor override; synthetic root aliases refuse. No actual
registered root or vendor request was created by this review.

Release blocker independently reproduced after research report:
Native unchanged funded_hold on identical100->101 source ratios gives net returns
0.007982017982018697 (83 names),0.00798201798201248 (412 names), and
0.00798201798201803 (SPY). Native excess is+6.217248937900877e-15 vs EW and
+6.661338147750939e-16 vs SPY, so current strict float screen falsely passes.
Exact source/account policy yields net799/100100 on each and zero excess vs EW
and SPY. Both ties must fail the already frozen all-three strict-positive rule.
Existing tests all passing does not resolve that witnessed financial defect.
No actual economic observation, positive-alpha evidence or source study occurred.
All reviewer Python/test processes are now closed.

# ADR425 correction proposal — independent nonimplementing data review

Decision: APPROVE the proposed exact canonical-endpoint screen contract before
TDD/source edits. This is approval of the described contract, not unseen code.
The release-blocking original witness and review are preserved separately in
/tmp/qf-w45-s10-424-final-data.md. No live source or registered root is involved.

Use original canonical positive Decimal entry/exit closes, retained with their
source payloads, before float projection. For each of selected/EW/SPY, compute
M=mean(Fraction(exit_i)/Fraction(entry_i)) exactly. The unchanged funded original
account's terminal return is M*(1-1/1000)/(1+1/1000)-1 = M*999/1001-1.
Compute all three benchmark excesses exactly (cash return zero) and apply the
same strict >0 to those exact quantities. Identical100->101 ratios must yield
net799/100100 for every cardinality, exact zero EW/SPY excess and FAIL.

Retain the unchanged funded_hold binary64 account outputs/equity paths/fees/
turnover/drawdown for legacy account reporting. Retain exact rational net returns
and net excess as explicit authoritative screen evidence. If net_excess remains
float-shaped for reporting, it must be a projection of the exact difference,
not a subtraction of independently rounded account totals. Clearly state the
basis distinction; native account totals can differ by rounding from exact
canonical-endpoint screen numbers. No post-hoc epsilon, tolerance, threshold
weakening, cost/horizon change, reranking, pooling or new economic trial follows.

The pre-existing complete64-label/413-series source/DQ/data evidence remains a
prerequisite. Required tests must observe the integrated identical-source false
PASS as RED before changing the screen, then verify FAIL and retained rational
identity. Also retain decisive positive and negative excess controls and a
Fraction property linking exact canonical endpoints to the frozen unit/cost
formula. Check variable entry prices so exact arithmetic applies ratios per
name before averaging, rather than dividing basket-average exit by basket-
average entry. Source/clock/no-retry and all old policy hashes remain unchanged.

Exact arithmetic does not certify vendor truth, PIT, or inferential alpha. The
next actual economic observation remains418's single final window. Source-policy
normalization and costs remain as registered. This corrects the computation of
the existing strict screen rather than changing its scientific acceptance bar.

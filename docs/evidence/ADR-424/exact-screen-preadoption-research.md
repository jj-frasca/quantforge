# ADR425 proposed exact economic-screen contract — preadoption research review

Verdict: APPROVE the proposed narrow contract before adoption and before implementation. Reviewer independently discovered the actual exact-tie falsePASS in the frozen424 implementation and is not the implementer. This is proposal review; final source/test/artifact verification remains required.

## Demonstrated problem and scope

With identical canonical paths100->101, native funded_hold net returns differ by portfolio cardinality83/412/1 because of floating aggregation. Their literal float differences currently pass the all-three screen despite exact equality. Keep ADR424 accepted text and immutable418 geometry; document this concrete methodology finding and a separate ADR425 BEFORE the fix. The correction is one evaluation-decision defect, not a new market hypothesis, variant, source acquisition, economic trial, cohort replacement or threshold change.

## Approved arithmetic contract

Use original canonical Decimal entry and exit prices from every validated source, rather than a float dataframe or Decimal(str(already-rounded-float)). Exact Fraction conversion represents those finite six-decimal source operands. For each of selected, all eligible and SPY:

R_gross_plus_one = mean_i(P_exit_i/P_entry_i)
R_net = R_gross_plus_one * (999/1001) - 1

Here c=Fraction(1,1000), and (1-c)/(1+c)=999/1001. This is algebraically the SAME equal-initial-dollar, fixed-normalized-unit account with entry fee funded from capital and exit liquidation fee, not a rebalanced account or a replacement cost model. Endpoint ratios correctly suffice for terminal cash; original native funded_hold equity paths, drawdown, fees, turnover and other account reports must remain unchanged.

Compute exact selected-minus-EW, selected-minus-SPY and selected-minus-cash (cash return0) as Fractions. Decide PASS using strict exact positivity against ALL THREE. Rational equalities must FAIL, arbitrarily small strict positive/negative contrasts preserve their true signs, and no epsilon or significance/tolerance threshold is introduced. The literal10bp economic assumption is unchanged; the historical binary64 companion calculation remains an explicitly retained approximation.

Reported net_excess may become float(exact contrast) under the proposed contract, provided every exact net return and contrast is also retained as canonical rational strings and documentation identifies the independently computed basis. Do not present the float contrast as necessarily bit-identical to subtraction of native account fields. Exact evidence remains authoritative for the strict decision if a very small contrast projects to displayed0; never infer the decision back from that projection. If a projection cannot serialize as finite, fail the method rather than invent or clip an economic result. This introduces no new numerical acceptance threshold.

## Required pre-code and final verification

Record the hypothesis of eliminating exact-tie falsePASS, unchanged comparator/selection/trials/geometry/costs and acceptance before experiments. Observe an actual collected RED through the full413-source/64-label evaluator for all-rising-identical prices, proving current screenTrue while mathematical oracle requiresFalse. Then implement narrowly.

Final tests/oracles must include all-rising exact ties and original flat ties, dominant selected-leg positive result, exact negative and arbitrarily small positive contrasts against matched controls, cash threshold after funded two-sided costs, and financial properties against an independent Fraction formula. Verify canonical Decimal operands survive before float projection, all required names remain included, and exact return means use83/412/1 respectively. Preserve original funded_hold source and every native account report; compare complete existing synthetic native account claims where captured. Retain exact ratios/contrasts and actual TDD receipts with the final artifacts.

Window checks still precede economics and publication. Additional exact computation must not bypass end-window checks or publish partial results on deadline crossing. First-source-failure, storage/method propagation, exclusive root/START, source-policy hashes, own-publication proof, no-live-test boundary and immutable418 protocols/cohort remain binding. The correction neither authorizes a real source invocation now nor resolves source completeness or alpha.

No product edits, imports, tests, HTTP or production-root actions were performed for this preadoption review; only this /tmp memo was written. Parent must obtain final independent conformance review after actual TDD implementation.

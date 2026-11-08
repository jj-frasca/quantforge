# ADR424 independent final research review — blocker pending

Current verdict: BLOCKED on a reproduced economic-screen precision error. This receipt does not approve the frozen original implementation. All reviewer tests/imports are CLOSED.

Reviewed original frozen module d9a6a2d5e7b75ce89469a7bce7d6a4da873db1482404fad44b294c74cf9058fb, CLI54e8721c377c0f275218dbf472ab5b6c1915e0e2d88490cc793f2a2d5bdb0798, tests2f608c77fa50933dd03c6fe70425a1feaef551b0aeb8ca143a7a8f9c996f428b. Independent unchanged focused suite35PASS22.34s, /tmp/qf-w45-s10-424-independent-research-tests.log. This passing suite does not catch the blocker below.

## Concrete exact-tie false screen

An independent no-source two-close account oracle used canonical price100 followed by101, identically for every constituent and SPY, and the original83 selected/412 eligible/1 benchmark cardinalities. Funded_hold reports net returns respectively:

- top83:0.007982017982018697
- EW412:0.00798201798201248
- SPY1:0.00798201798201803

Current float subtraction produces selected-minus-EW6.217248937900877e-15 and selected-minus-SPY6.661338147750939e-16. All three mathematically share exact net return (101/100)*(999/1001)-1, yet the current all(value>0) screen passes because cash excess is positive too. This is a concrete positive exact-tie falsePASS arising from floating aggregation at different portfolio cardinalities, not a suggested arbitrary tolerance or a statistical-significance threshold.

The bounded correction should preserve pinned funded_hold arithmetic/results and the fixed economic policy, while deciding strict economic signs from an independent exact Fraction cash-account comparison over canonical price operands, using the original equal-dollar fixed-unit formula and the literal fixed cost1/1000. No epsilon, threshold relaxation, alternate source or new economic look is needed. First record the written finding and actual new collected RED for an all-rising-identical synthetic tie through the full evaluator. Then verify positive and negative comparisons, exact tie rejection, original costs and unchanged report accounts. Final review must check this fix and its retained artifacts before approval.

## Other text conformance checked

Preflight binds exact compressed/raw cohort, protocol, archived7048 inputs and complete original records/selection, own seal publication and pinned24-path active code inventory. It retains actualHEAD/application/dependencies/Decimal/default identities. No current score parser/scorer recomputes ranks. Production CLI has no input/root/vendor/window overrides, checks early clock before preparation and constructs default adapter only after durable exclusive START. Synthetic API rejects registered path and aliases. Root and receipt writes fsync appropriate directory boundaries. Clock checks after START and attempt writes prevent acquisition after those operations cross the end. Request crossing preserves source/report then stops INCOMPLETE, and account crossing suppresses economic publication. Original quality warnings and passing dataset evidence precede calendar refusal; expected failures stop before another name, unexpected/storage errors propagate incomplete. Source order/bounds/exact64-label requirement and unchanged funded_hold costs/exposure are coherent.

Independently verified original immutable ADR418 SHA0e7783384c117845cee7bdb5acbfb333d3901feb6035587436a41aa14bdda811 and cohort gzip2aaf841c39d5dfaae94d56c7a7ef2a312f34cb9a80bb7e36fbcc7d2622031f97. No source/root or market activity by reviewer. Synthetic tests do not improve alpha; next economic observation remains February11 final screen.

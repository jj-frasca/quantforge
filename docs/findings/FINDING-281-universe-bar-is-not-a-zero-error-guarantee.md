# FINDING-281: The universe bar is not a zero-error guarantee

- **Date:** 2026-10-20
- **Status:** Resolved by documentation correction
- **Scope:** expected_max_sharpe_under_null source-facing methodology claim

## Claim and counterexample

The function's docstring said the independence-based bar “never lets selection
luck through.” It also described the Gaussian scale as the expected maximum
without qualifying finite-N approximation. These are stronger claims than the
implemented formula supports.

In the idealized model of N independent standard Normal draws Z, let
z=sqrt(2lnN). Then

```text
P(max Z > z) = 1 - Phi(z)**N > 0, for every finite N>=2.
```

For N=607 this is approximately 0.0990028183783648. The dimensionless scale
removes the positive history factor SE from both sides. A source-model
counterexample is sufficient to refute a deterministic exclusion guarantee;
correlation in actual equities does not supply that missing guarantee.

Parent SciPy and independent standard-library erfc calculations agree. A
self-contained reproduction with no sampling, provider or search call:

```python
import math

for n in (2, 50, 200, 607):
    z = math.sqrt(2 * math.log(n))
    tail = math.erfc(z / math.sqrt(2)) / 2
    probability = -math.expm1(n * math.log1p(-tail))
    print(n, probability)
```

The four probabilities are approximately 0.22474783, 0.12107485, 0.10714027
and 0.09900282. These are analytic idealized standalone single-bar probabilities,
not Monte Carlo measurements or observed QuantForge false-graduation rates.

## Interpretation and correction

sqrt(2lnN) is a leading-order Gaussian extreme-value scale, not the exact
finite-N expected maximum or a cutoff chosen for a specified alpha. Lo's
asymptotic iid standard-error expression reduces algebraically to sqrt(1/T)
at true Sharpe zero; it is not an exact finite-sample Gaussian law for estimated
Sharpe. Independence and marginal distribution assumptions remain substantive.

The source docstring and active cold memory now state these limits. Clearing
the annotation does not prove skill or eliminate selection luck. Composite gate
Type-I error remains a separate, procedure-specific empirical question. This
finding neither supplies that rate nor proposes changing any bar or threshold.
The historical accepted ADR-018 remains untouched; its formula, function name,
runtime defaults, gate logic and accounting-v14 remain unchanged.

## Verification

The analytic counterexample and independent review preceded documentation edits.
This slice adds no executable behavior or prose-mirroring unit test. Verification
must preserve the complete runtime AST after restoring the original docstring
and pass foreground make check-all before individual publication and exact CI.
Parent and independent review both confirmed exact prior runtime AST preservation
after restoring only the target docstring, and reproduced all four analytic
values. Independent final three-path review approved the scientific qualifications.
Foreground make check-all passed 13,466 backend and 566 frontend tests with lint,
formatting and types green. Source SHA256:
b816dcf0825abd243ece5690d4c5a0bb2974fa19f7d6abf3510edbf93af7b031.

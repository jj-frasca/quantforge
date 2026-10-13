# FINDING-219: Native wider benchmark moments erase or distort beta

- **Status:** Corrected for matched native wider beta moments
- **Date:** 2026-10-12
- **Review:** Codex autonomous session 4, ISO 2026-W42
- **Decision:** ADR-270
- **Prior art:** nonconstant wider precision limitation disclosed in FINDING-218

## Written finding and causal evidence

For original longdouble [base,nextafter(base,+inf),nextafter(previous,+inf)],
the input is genuinely nonconstant even when all float64 conversions are equal.
Same-series beta is exactly one under an oracle built from each original scalar's
as_integer_ratio and exact Fraction-centered covariance/variance.

| Origin | Published beta | Exact beta | Covariance-only replacement beta |
|---|---|---|---|
| 1 | 0 | 1 | .4 |
| .1 | about .880141 | 1 | about 3.5e-7 |
| .5 | 0 | 1 | .4 |

Primary installed pandas source explains both losses: Series.cov extracts arrays
with dtype=float, and nanvar reduces the mean and squared-deviation sum with
np.float64 before casting back to the source dtype. A wider return dtype does not
prove wider arithmetic. A covariance-only fix was independently rejected because
its original variance denominator is also biased. All wrong beta values are finite.
These synthetic public-kernel reproductions do not establish historical market
contamination or authorize rewriting generated records.

## Narrow correction and limits

For actual native wider floating sources only, use original aligned native arrays,
translate each by its first observation, center natively and divide matched native
cross-product/squared-deviation sums before float conversion. The n-1 sample divisors
cancel. Keep constants and all ordinary/nullable paths plus other formulas intact.
Needed wider underflow or invalid denominator refuses instead of falling back to
narrowed arrays; other precision/source/strict-state limitations remain disclosed.
No variance epsilon, threshold, source repair or calibration identity change.

The ratio uses no unused strategy self-variance. Thus a tiny strategy whose final
float beta correctly rounds to zero remains usable when its cross-product is
measurable, even if a full covariance matrix would underflow in an unused diagonal.
A needed native denominator outside float64 range stays native through division.
Other mathematically finite betas may still be declined when needed arithmetic is
unmeasurable; this does not certify universal covariance accuracy.

## Verification

Independent scratch approval: 224 exact represented-source Fraction probes and 160
complete ordinary/nullable baseline comparisons, with tiny-strategy zero, native
non-float64 denominator and needed-underflow refusal probes. Tests and ADR are
written before production. Initial RED: 29 failures and 21 preserved cases. The later focused run showed
that four failures were an unrelated, preexisting wide-plus-nullable subtraction
KeyError before beta; 25 initial failures concerned this beta correction.
Pre-code review strengthened the property domain: native NumPy array operations
and explicit nonconstant assertions avoid upstream pandas scalar-promotion loss
and vacuous constant cases. Tiny fixtures distinguish precision from exponent
range for wider-but-not-extended platforms. Already-rounded upstream observations
cannot be recovered by this beta correction. Final pre-code run retained those same 29 failures/21 passes. After implementation,
165 affected tests passed and four unsupported mixed nullable pairs failed before
beta. The six mixed-partner assertions now use supported native float64/float32/
int64 partners, with no skips, deletions or weakened numeric assertions. An isolated
published-baseline rerun observed 29 genuine beta failures and 21 preserved cases
with the corrected fixtures, before any further production change. Final affected
benchmark/API suite: 169 tests pass. Independent final review approved 140
targeted tests, 224 actual public-implementation exact-source wider/native mixed
Fraction oracle probes and 160 complete exact nonwide ordinary/nullable baseline
comparisons. Needed-underflow ValueError/caller state, native denominators outside
float64 range and correctly rounded tiny strategy beta zero pass. Production AST
outside the helper and scoped beta construction restores to the published baseline.
Foreground `make check-all PYTEST_WORKERS=4` passed: 5,619 backend tests,
363 frontend tests, backend coverage 97.72% and frontend statement coverage
97.63%, with all lint/type/format checks green. Exact master CI is checked
after individual delivery.

Separate limitation: installed pandas cannot subtract a native wider floating
Series and a nullable Float64/Float32 Series, raising KeyError for float128. This
preexisting excess-return incompatibility remains outside the beta-only correction.
Ordinary nullable pairs retain their original behavior; successful mixed wider
comparisons here concern native NumPy partner dtypes.

# ADR-313: Attribute corrected band simple-mean sign references end to end

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Codex autonomous session 30, ISO 2026-W42
- **Extends:** ADR-042/055/061/103/158/308/310/311/312
- **Relates to:** FINDING-159

## Context and alternatives

Historical band references sign a conditional log mean while scoring simple
returns, and the historical observable recursion has a different startup prior.
ADR-310 supplies a separately named known-start full-price posterior. Releasing
another isolated scorer would leave production attribution incomplete. Silently
replacing legacy scores would restate historical measurements. Adopt a complete
explicit opt-in instead, preserving legacy defaults and all historical artifacts.

## Decision: closed identity and compatibility

Add optional nullable band_reference to PowerCalibration and PowerSweep. Its
frozen, always-revalidated, extra-forbid BandReference object has literal method
band_conditional_simple_mean_sign_zero_start_v1 and explicit drift, total_vol,
start_price. Absent/null historical metadata stays unknown, including externally
supplied arrays. Never infer provenance from edge labels or prices.

Validate original finite nonboolean Real scalars before normalizing to Python
float. Require original and normalized positive total_vol/start_price/half_life,
0<deviation_share<=1; drift is signed finite. Ordinary finite rounding of drift
including to zero is accepted. Reject original share<1 rounding to1, preserving
positive level noise. Known cells require edge band_reversion, phi absent,
half_life/share present, and no simultaneous AR reference. Check original
conditional coordinates before existing model scalar normalization. Sweep headers
and reconstructed cells agree on common method/law and edge, including unchecked
copies and empty sweeps. Half-life/share remain per-cell coordinates.

Collection reconstructs cells and refuses unequal known/unknown/common identities.
Capture comparison retains existing reconstruction, header/search/AR/key/cell/history
checks in their relative order; band identity follows AR identity. After structural
checks and before any row arithmetic, refuse unequal shares for all matched known
band half-life keys. Unmatched cells retain existing no-delta rows. None/None
retains historical permissiveness. Detection-only probability comparison retains
all current formulas/guards; reference identity is separate from search/gate/v14.

## Fixed nominal source law and sign arithmetic

For normalized Python-float h, share, total_vol use the unchanged generator recipe:

```python
rho = 0.5 ** (1.0 / h)
deviation_vol = total_vol * np.sqrt(share / (2.0 * (1.0 - rho)))
level_vol = total_vol * np.sqrt(1.0 - share)
```

Validate all intermediate domains/finiteness, stationary rho and positive deviation
noise; normalized share<1 requires positive level_vol and R. Share1 genuinely
permits zero level noise. Use ADR-310's nominal binary64 q=deviation_vol squared
multiplied by (1-rho squared), R=level_vol squared. Validate its complete derived
law even for empty observations before CLI generation. The historical sampled
innovation scale deviation_vol*np.sqrt(1-rho**2) remains byte-exact; squaring its
rounded value need not equal nominal q bitwise. This method conditions a declared
nominal Gaussian law, without certifying exact finite-arithmetic source equivalence.

For available prediction index i>=1, previous latent d[i-1] or full-price posterior
mean/variance at i-1 supplies the state. Only index0 is unavailable/flat. Fix:

```text
delta=rho-1.0; delta_square=delta*delta
m_product=delta*previous_state; m=drift+m_product
base_variance=q+R
latent V=base_variance
observed component=delta_square*previous_posterior_variance
observed V=base_variance+component
doubled=2.0*m; score=doubled+V
```

Require every intermediate finite, V positive, and reject positive previous
posterior variance whose component becomes zero. Other finite rounding is accepted,
including a nonzero component absorbed in the variance sum. No fallback, clipping,
noise floor, epsilon, fitting, expm1 magnitude or alternate arithmetic.

For Gaussian log return m,V, sign(E[simple return])=sign(2*m+V). Under ordinary
correctly rounded binary64 with gradual underflow, finite doubling is exact;
nonzero exact addition lies on the minimum-subnormal lattice, so finite executed
score has the same sign as exact Fraction(2*m)+Fraction(V). This guarantee is for
computed binary64 m,V only, not earlier model arithmetic or arbitrary environments.
The score is solely a sign score, never an expected-return magnitude.

## Central dispatch, preflight and CLI

measure_power accepts optional band_reference plus band_deviations. Known mode
requires exact source/deviation mapping keys and forbids phi, AR reference,
external gross/net/observable score arrays and contradictory/missing coordinates.
Deviation evidence without known mode refuses. Before ANY scorer/search, validate
all mode/law/source/prediction evidence for every symbol. Snapshot owned frames
and deviations; original dtype/value/mask evidence must be real numeric, complete,
finite and nonboolean, with exact unique ascending matching indexes and one
deviation per close. This mode supports NumPy-backed numeric columns; object-backed
or unsupported extension evidence refuses without coercion. Closes are positive before and after binary64 normalization;
logs need only be finite. Validate derived returns consistently with the existing
scorer. Prediction, scoring and search consume the same owned normalized snapshots.
No direct-caller check certifies that supplied latent states generated the prices.

Use unchanged oracle_sharpe_of for latent gross cost0, latent net and observed net
DEFAULT_COST_RATE, after all-symbol preflight. Keep full measured-frame history,
turnover, annualization, no extra lag and all search/detection/count-tail operations.
Default legacy measurement and generator/scorer/posterior bodies remain exact.

Horizon CLI adds --band-reference-method legacy|conditional_simple_mean and
--drift/--total-vol/--start-price, all registered as value-position flags. Legacy
omission/explicit legacy retains exact old calls and forbids new law overrides.
Conditional requires all three explicit law flags; validate the whole nominal law
before first generation, pass the same normalized recorded inputs to generation
and measurement, hand off existing PlantedEdge.deviation, and do not invoke old
external scorers in that branch. No workflow changes or actual source runs.

## Consumers, evidence and reversal

All human reports identify explicit method/common law or unknown, and per-cell
half-life/share as needed. API inheritance retains metadata. Frontend nested Zod
shape is strict, optional/nullable at header/cell and preserves deviation_share;
backend owns scientific coherence/ranges. Captions distinguish latent gross/net
and full-price observed NET simple-mean sign references from unknown historical
driver conventions, preserve AR308, exact served values and duplicate rows, show
law via String(value), and retain selection-bias/nonoptimality and compatibility
qualifications. Search MATCHED does not certify reference equivalence.

Actual RED precedes implementation. Test exact Fraction sign properties including
subnormals/cancellation/overflow refusal, independent joint-Gaussian predictions,
first-return indexing, state uncertainty, zero-noise law, original/normalized
scalar/source guards, all-symbol preflight, immutable snapshots and NumPy policy.
Mock source/scorer/search CLI flow; test identity/unchecked copies/collector/share
refusals, unchanged detection inference, API/Zod/caption flow and legacy call lists.
Preserve prechange historical semantic fixtures/raw hashes and old source/scorer/
posterior ASTs; no cohort reruns. Independent research/frontend reviews, full
foreground make check-all, individual publication and exact master CI are required.

No generated record, threshold, v14, search/gate fingerprint or historical score
changes. F159's supported production correction gap can close after verification;
historical qualifications and arbitrary provenance/optimality limits remain. No
new power measurement, cost-aware optimum, sample maximum or no-edge result is
claimed. Reverse by removing opt-in production while retaining attributed readers;
never silently strip method identity or relabel stored evidence.

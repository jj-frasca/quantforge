# ADR-267: Validate durable IC summary domains and statistic coherence

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 3, ISO 2026-W42
- **Resolves:** FINDING-216
- **Extends:** ADR-035, ADR-145, ADR-266

## Context

The summary producer now checks original observations, but ICSummary construction,
unchecked copies and nested durable reconstruction still accept nonfinite fields,
negative dispersion, impossible hit rates/counts and contradictory redundant IR/t
claims. JsonFileCrossSectionalStore reconstructs incoming graphs before writing;
its existing boundary cannot enforce missing leaf invariants. NaN metadata can
reach nonstandard JSON. A read-only census of 23 committed experiments found 242
summaries, all finite and exactly coherent with the existing producer formulas.

## Options Considered

1. Validate the leaf and revalidate instantiated leaves at certified boundaries.
   - Pro: protects construction, nested claims and existing JSON-store prewrite
     checks without duplicating rules or changing persistence shape.
   - Con: intentionally declines coercible float/string/bool period counts and
     historically incoherent metadata; model_copy remains unchecked by design.
2. Validate only summarize_ic or the JSON writer.
   - Pro: fewer model rules.
   - Con: direct construction and other reconstruction paths retain bad claims.
3. Enforce an exact [-1,1] model mean now.
   - Pro: stronger apparent correlation-domain assertion.
   - Con: rejects coherent pre-ADR-266 endpoint roundoff. A new arbitrary tolerance
     or historical normalization would introduce a separate unsupported policy.

## Decision

Keep the frozen leaf, add revalidate_instances='always', require every float field
finite, std nonnegative and hit_rate in [0,1]. Require native Integral n_periods,
excluding Python/NumPy bool, normalize accepted integers to Python int, and retain
the producer's existing minimum of two observations. Float/string counts are
explicitly declined rather than silently coerced. No minimum sample threshold changes.

Require exact information_ratio == mean / max(std, _MIN_STD) and exact
 t_stat == information_ratio * float(np.sqrt(n_periods)), using the producer's
unchanged operations. Arithmetic TypeError, OverflowError or FloatingPointError
becomes ValueError; a nonfinite expectation cannot match a finite claimed field.
Keep _MIN_STD=1e-12 and legitimate finite constant-series IR/t values unchanged.
No statistic is repaired, recalculated for storage or rounded to pass.

The mean is finite only at this leaf. Coherent pre-266 mean=1+ULP metadata retains
its original evidence. An impossible but finite/coherent mean remains a disclosed
limitation; do not claim universal correlation-domain certification. ADR-266's
strict original-observation validation continues at the actual source helper.

The only existing synthetic endpoint fixture with inconsistent t metadata is updated
to the unchanged producer formula, preserving its endpoint and absent-IC assertions.
No store/schema-field/selector/sizing/gate/calibration identity changes or generated
record edits. InMemory store behavior remains outside this leaf-only change.

## Evidence, consequences and reversal

Independent pre-code approval validated all 242 committed summaries exactly, coherent
historical endpoint metadata, all 16 generators/45 configurations, NumPy integer
compatibility, malformed copies, nested attachment and scratch prewrite preservation.
Observe genuine RED for native domains, short/unchecked claims, one-ULP redundant
stat contradictions and unrepresentable count arithmetic. Verify all-or-nothing JSON
writes/reload in temporary directories, frozen/absent/legacy shape, exact producer
statistics including std floor, Hypothesis observations, focused and foreground full
gates, independent final review and exact master CI after delivery.

Reversal restores the permissive leaf and reopens FINDING-216; original statistics,
calibration identity and durable field names remain unchanged either way.

# ADR-375: Persist effective optional single-name admission rubrics

- **Status:** Accepted
- **Date:** 2026-10-26
- **Deciders:** Codex autonomous session1, ISO2026-W44
- **Addresses:** FINDING-317 (surviving-row rubric lineage only)
- **Extends:** ADR-023, ADR-029, ADR-137, ADR-147, ADR-150, ADR-372, ADR-374

## Context

Different optional pre-screen policies can produce identical stored experiments.
Config version hashes exist but are not retained with surviving rows. CLI minimum
logging is partial external context. No affected actual screened cohort is known;
full universe replay additionally needs roster, source/cutoff and outcome evidence.
Research and data-engineering reviews support a bounded rubric snapshot without
introducing another run-artifact writer or claiming complete admission provenance.

## Options Considered

1. **Add nullable effective rubric evidence to each Experiment.**
   - Pro: uses existing validated stores/retention, preserves historical unknown
     state, and makes surviving-row policy differences durable without a writer.
   - Con: repeats small configs per row; zero-survivor runs and pruned rows leave
     no policy archive, and quality input/roster/outcomes remain unrecorded.
2. **Introduce a run-level admission artifact with complete outcomes.**
   - Pro: can cover requested, filtered and failed names, including empty runs.
   - Con: needs run identity, source snapshots, writer/atomicity/retention and
     orphan policies, substantially beyond this confirmed rubric-loss correction.
3. **Put policy JSON in rationale or retain CLI minima alone.**
   - Pro: smaller schema surface.
   - Con: unvalidated prose and partial logs do not define an immutable rubric;
     programmatic policies and full optional flags remain ambiguous.

## Decision

Add a frozen AdmissionPolicy with REQUIRED nullable value_config and
quality_config fields, holding complete ValueGateConfig/QualityGateConfig
snapshots. Experiment.admission_policy defaults to None: historical or direct
search policy is unknown. A present object with both fields null explicitly
records no effective optional screen. Each effective config requires its existing
provider is not None AND config is not None; mirror those guards exactly, even
for a falsey callable provider. Supplied but inactive configs remain ignored.
Existing per-config version_hash derives from the complete snapshot; no redundant
hash field or change to the technical gate/manifest hash is introduced.

Before nested normalization, reconstruct through the expected concrete config
class and require canonical finite JSON equality between the original Python
model dump/raw mapping and reconstructed complete dump. Use sorted ordinary JSON
with allow_nan=False; no lossy mode=json, custom encoder or default=str. This
preserves ordinary constructor coercions already reflected in model fields and
refuses silent reinterpretation of unchecked values, omitted defaults or extras.
For example, an unchecked keep_unscored string must not be silently recorded
as a different boolean rubric. ValueScreen can itself coerce such strings: 'false'
is filtered before attachment, while 'true' reaches the new refusal boundary. Raw JSON integer minimum1 may refuse versus canonical1.0;
ValueGateConfig(min_score=1) already stores1.0 and remains valid. Finite JSON-
equivalent NumPy float64 may remain accepted; arbitrary native types are not
certified. Unsupported/noncanonical active snapshots refuse rather than become
inactive, unknown or missingness fallbacks.

AdmissionPolicy revalidates instances and nested configs, forbids extra outer
fields and requires both keys even when null. Include it in Experiment's existing
defensive claim reconstruction. Attach effective snapshots with manifest metadata
inside the existing per-symbol try, after search; do not reorder callbacks,
screens/acquisition/search or validate inactive configs. Preserve all screen
formulas, finite thresholds/coercions, defaults, technical hashes, v14 and stores.

## Consequences

New surviving universe rows distinguish effective policies, including known off.
Historical absence stays unknown with no generated migration. Existing stores
retain evidence only with its row; old readers may ignore/drop the additive field
when rewriting, so downgrade writes are not a preservation guarantee. Public
projected APIs do not expose this new field in this slice.

Malformed active unchecked configs can refuse evidence attachment after search,
becoming per-symbol errors under ADR-374 without a stored row or recovered trial
history. Such configs may still filter names before attachment. This is an
explicit availability tradeoff and a surviving-row rubric contract, not global
admission validation, source certification or full roster/outcome replay.

Write failing tests before source, including effective guard geometry, falsey
providers, distinct stored rubrics, required-nullable keys, canonical evidence,
untrusted copies, immutable ownership, store round trips and historical unknowns.
Audit all existing committed pool rows without writes; strip only the new absent
field when comparing canonical old payloads. Replay ordinary orchestration controls
with only the additive field removed, retain all source hashes, obtain final
research/data reviews and run foreground make check-all before individual push.
Reverse by stopping attachment while preserving nullable readers; dropping readers
can discard evidence and requires an explicit follow-up decision.

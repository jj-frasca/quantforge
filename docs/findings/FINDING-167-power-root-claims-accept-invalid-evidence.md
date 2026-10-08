# FINDING-167: Power root claims accept invalid evidence

- **Date:** 2026-10-08
- **Severity:** High — durable power measurement validity
- **Status:** Resolved by ADR-218
- **Reproduced revision:** `68cf8f68`

PowerCalibration accepts a boolean searched count coerced to one, negative
counts, detected counts exceeding searched symbols, survivors exceeding detected
symbols, NaN detection rates, infinite deflation bars and rates disagreeing with
the count ratio. For two searched symbols it accepts three detections and a rate
of 1.5. These durable root claims describe no coherent experiment, yet frozen
containers and authoritative sweep reconstruction cannot reject them.

These are malformed synthetic boundary inputs. All 12 committed power cells
satisfy the proposed root contracts; no observed corrupted artifact or incorrect
published detection rate is claimed. ADR-218 applies the analogous established
null-root guards: original count/score types and bounds, ordered counts, and an
exact detection ratio, without substituting or filtering evidence.

Optional legacy arrays remain supported. Array/reference/process-parameter
validity, component relationships and derived bar recomputation stay separate.
No sample, statistic, threshold, fingerprint, reference rule or generated record
changes are proposed.

## Correction and verification

Forty root/sweep rejection cases failed before implementation, with six
coherent compatibility/property cases passing. The correction reuses existing
original-evidence guards and enforces ordered counts plus the exact rate.
Seventy-seven focused root, probability-comparison and endpoint tests pass;
all 12 committed power cells satisfy the contracts read-only. Independent final
review and the full foreground gate are required before delivery. No threshold,
methodology identity, array semantics or generated artifact changes.

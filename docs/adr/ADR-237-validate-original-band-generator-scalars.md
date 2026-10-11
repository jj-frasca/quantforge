# ADR-237: Validate original band-generator model scalars

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 31, ISO 2026-W41
- **Resolves:** FINDING-187
- **Extends:** ADR-042, ADR-061, ADR-235

## Context

Band-source construction can erase invalid original model provenance before the
filter sees it. Boolean half-life, deviation share, total volatility and start
price each produce finite sources and reference scores. Validating derived rho,
volatility and observed logarithms cannot identify those original boolean inputs.

## Options Considered

1. Validate original model scalars before deriving the source. Narrow, preserves
   native arithmetic, but rejects malformed direct callers.
2. Rely on filter/source checks. Misses provenance erased by source construction.
3. Coerce or replace generator inputs. Changes source laws or fabricates evidence;
   rejected.

## Decision

After the existing n_bars check, require original finite float-representable real
nonboolean half_life before its existing positive range comparison. Require the
same original evidence for deviation_share before its existing (0,1] comparison.
Then validate total_vol, drift and start_price before RNG/source construction.
Use the shared finite scalar guard for inspection only; retain original operands
in domain comparisons and all generator/filter arithmetic. Valid range errors
retain their existing order; original scalar validity takes precedence over its
own range comparison. No new parameter domain, conversion or source fitting is
introduced. The existing n_bars error retains precedence on short invalid calls.

This is original model evidence validation, not derived generator overflow or
general mixed-type recovery. Preserve seeded draws, source fields, initialization,
latent/filtered means and reference scores for valid native inputs. Do not change
thresholds, fingerprints, defaults, frozen cohorts or historical artifacts.
FINDING-155 and FINDING-159 remain Open for their separate reference qualifications.

## Verification

Record pre-code invalid-original-scalar refusal failures and preserved domain,
seeded source, native scalar and reference cases. Include boolean Hypothesis
refusal and exact negative Fraction range comparisons. Independent review checks
native producer fields and gross/net scores. Full foreground make check-all,
explicit-path commit, fresh sync, individual push and exact CI precede completion.

## Consequences and reversal

Invalid original source-law inputs cannot obtain measured band-reference claims
through arithmetic coercion. Removing the validation calls reopens FINDING-187;
no historical experiment is reinterpreted.

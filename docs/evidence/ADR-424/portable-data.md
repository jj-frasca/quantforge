# ADR424 independent portable evidence linkage review

Decision: APPROVE the portable original-input/pinned-policy representation. This
changes runtime availability of already frozen bytes, not source, normalization,
quality, selection, costs, cohort, thresholds or economic geometry. A shallow CI
checkout need not possess original7048 Git objects when the original complete
bytes and fixed identities are retained.

Using only the standard library and read-only local Git object access, I verified:

- pinned-policy.json exact SHA256 is
  3d2e321c6b596352bc9f44d0f47e295698ca1969799ced816fa387be6308a4b0.
- All24 active policy file digests equal their bytes at revision
  7048c785fd34fa0fc5b8357fc711929c7fe48fb9 AND current working-file bytes.
- input-fundamentals.json.gz is436389 bytes, compressed SHA
  377d45de1df67a2d5624355d0391c85fa0bde32ab0a6d6b59f1dd69b31ddfa1c.
  Its COMPLETE decompressed contents equal Git7048:data/fundamentals_pool.json
  byte-for-byte, raw SHA
  b59375cd295f2d7582bed762b856f1f496cdc246d94b916e32025cb2069d4ff6.
- input-roster.txt.gz is1130 bytes, compressed SHA
  ff2f6cc6c68a32e8ebc5c63b3caf34dedb2c9225766519d0ff4024578739131b.
  Its COMPLETE decompressed contents equal Git7048:data/universes/sp500.txt
  byte-for-byte, raw SHA
  ee973b82b0fba4471d6c248330929dfc0c8e4589aeb3e0cea678c1e042b38040.

I also inspected imports in adapter/normalizer/canonical-model/DQ/frame/dataset/
account/engine/panel sources. The24-file set covers the intended active policy
and includes relevant package initializers, types, immutable-JSON helpers and
trial-count boundaries. It is deliberately NOT the complete import graph:
published_portfolio imports evolving fundamental record/scorer modules, even
though funded_hold consumes none of those fundamental scores. Actual broader
application/module/dependency identities still need retention at execution, as
ADR424 already requires; source-code equality must not imply dependency or
vendor equivalence.

Runtime must bind the FIXED manifest SHA before trusting its listed entries,
verify compressed AND raw archive hashes, then verify active current-file hashes.
Only those full original blobs may establish record/roster/selection equality;
no fallback to current data paths, a network request or an unpinned Git revision.
Preserve existing independent own-seal publication proof checks and actual code/
lock/default-policy/Decimal/runtime identities before root/provider creation.

The immutable418 raw/gzip cohort and source window are unchanged; registered root
remains absent. No app imports, tests, HTTP, prices, study economics, source calls
or repository data edits were performed for this review. The only write is this
review receipt in /tmp. Final implementation conformance review remains required.

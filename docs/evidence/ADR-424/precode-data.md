# ADR424 independent nonimplementing data precode review

Decision: APPROVE the exact ADR424 contract for offline implementation. This is
not approval to execute the real ADR418 source attempt now. Reviewer did not
implement or formulate the ADR424 design; inspection used text, Git-independent
standard-library decompression/hashing and saved publication metadata only. No
application imports, tests, HTTP, source request, market prices or actual study
economics were performed. The registered production root is absent.

Read .claude/agents/data-engineer.md, exact ADR424 and ADR418, and the relevant
canonical bar, original DQ, request-range and ADR424 data contracts. Decompressed
the immutable cohort solely as configuration. Its compressed SHA is
2aaf841c39d5dfaae94d56c7a7ef2a312f34cb9a80bb7e36fbcc7d2622031f97;
raw SHA is14b888b305bd233ef60ff56edd5dd14867d8ed265676908011a866cba18a9c28.
The sealed counts412/83/64, original half-open request bounds, strict screen,
one-attempt root and final UTC window agree with ADR424. The saved authoritative
own-seal metadata show fullSHA941dee7c2443f30e4433617a3d5070e6a8a80b60,
push CI42227612894 completed2026-11-06T13:46:49Z and hooks42227612864 completed
13:42:47Z, both before the original Nov9 14:30Z deadline.

The design correctly distinguishes pinned active7048 source/account code policy
from actual dependencies and the wider changed import graph. It preserves opaque
sealed scores rather than recomputing them with423 or current fundamentals. The
actual Git/code/lock/platform/distribution/Decimal/default-policy inventory must
be retained before the provider starts, while dependency equivalence to7048 is
explicitly unclaimed. A policy mismatch refuses before consuming the one root.

The exclusive durable START precedes provider construction and every request.
Window checks precede root/provider, each request and account computation/output.
Crossing the end boundary ends INCOMPLETE without additional requests or subset
accounts; saving received source/DQ diagnostics afterward does not license a new
look or completion. Expected fetch/quality/calendar failures are UNEVALUABLE;
write failures and unexpected method errors must propagate with the start left
incomplete. Durable source/report writes therefore cannot be inside the broad
source-failure classifier. Interrupted roots cannot resume.

Retain original canonical payloads, SHA256, one original full DQ report (including
UUID/time and warnings) and passing dataset evidence. All413 series must match
the exact64 ordered sealed session labels; no calendar repair or flag filtering.
Do not convert daily session labels to invented close-time instants. Synthetic
results remain clearly labelled and cannot improve the alpha case.

Implementation checks for final review (not additional protocol changes):
- Durability should flush/fsync START and its parent directory before constructing
  the provider; use exclusive JSON publication and never overwrite a winner.
- Synthetic production-root refusal must include resolved/symlink aliases, and
  production CLI must expose no input/root/clock/vendor override.
- Validate actual default quality/retry configuration and standard Decimal
  precision/rounding/traps without resetting mutated state or dropping warnings.
- Failure tests must prove zero provider/root effects on early/late/tampered
  preflight and distinguish source failure from disk/method error after START.

No precode blocker found. Final runtime/artifact review, actual TDD receipts,
protected-file equality and parent full gates/CI remain required before release.

# ADR-001: Monorepo with explicit scope cuts

- **Status**: Accepted
- **Date**: 2026-05-27
- **Deciders**: Joe Frasca

## Context
QuantForge spans a Python backend, a React frontend, architecture docs, and a codified
Claude Code context system that must stay in lockstep with the code it describes. It is a
single-maintainer project whose value is *methodological rigor*, not feature breadth. Two
risks must be managed up front: (1) layout that lets backend, frontend, and context docs
drift apart, and (2) unbounded scope that dilutes the validation story.

## Options Considered
1. **Monorepo (backend + frontend + docs + .claude in one repo).**
   - Pro: atomic cross-cutting commits; one CI; context docs live beside the code;
     one git history tells the whole story to a reviewer.
   - Con: larger repo; internal module boundaries must be enforced by discipline, not by
     repo separation.
2. **Polyrepo (separate backend and frontend repos).**
   - Pro: hard boundaries; independent deploy cadence.
   - Con: cross-cutting changes span repos; context system fragments; overkill for one dev.
3. **Backend-only repo (defer frontend indefinitely).**
   - Pro: smallest surface.
   - Con: the ValidationReport page is a core recruiting signal — cutting the frontend
     entirely weakens the deliverable.

## Decision
Use a **monorepo**, and make scope cuts **explicit and documented** (§3 of ARCHITECTURE.md):
no paper trading / live execution, no WebSocket streaming, no order book / OMS, no
LSTM/neural nets, no Reddit/FinBERT pipeline before Phase 8, no institutional execution
simulation. These omissions are deliberate, not gaps.

## Consequences
- One CI pipeline and one `make check` gate cover the whole project.
- The codified context system (CLAUDE.md + agents + cold memory) can reference code paths
  directly and is versioned with the code.
- Internal layering (data → research → validation) is enforced by convention and review,
  since the repo won't enforce it.
- A reviewer reading the repo sees the scope cuts and understands they were chosen to
  protect the rigor story — the absence of paper trading is a feature, not an oversight.

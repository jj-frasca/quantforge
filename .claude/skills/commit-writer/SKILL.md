---
name: commit-writer
description: >
  Draft and create a QuantForge commit from the staged diff, following
  docs/adr/COMMIT_TEMPLATE.md. Use when a logical unit is complete and the user has
  asked to commit. Scans the diff to populate WHY/WHAT/TESTS/EDGE CASES automatically.
---

# commit-writer

Turns a finished, staged change into a structured commit. The value over the bare
template is automation: read the diff and *write* the body, don't ask the user to.

## Procedure
1. **Inspect** — run in parallel:
   - `git status --short` (what's staged vs unstaged; watch for the other work track)
   - `git diff --staged` (the actual change to describe)
   - `git log --oneline -5` (match the repo's style)
2. **Stage deliberately** — add only the files belonging to THIS logical unit, by name.
   Never `git add -A`/`git add .`. Never stage `.env`, secrets, or unrelated changes.
   Production code and its tests go in the SAME commit (CLAUDE.md rule 2).
3. **Draft the body** from `docs/adr/COMMIT_TEMPLATE.md`:
   - `type`: feat / fix / refactor / test / docs / chore / infra / ci
   - `WHY`: infer the reason from the diff + session context (1–3 sentences)
   - `WHAT`: bullet the concrete changes
   - `TESTS`: list each new/changed test and what it validates
   - `EDGE CASES`: the explicit edge/error paths covered
   - `ADR:` line ONLY if this commit enacts an architecture decision
4. **Gate** — confirm `make check` passed (lint + tests + coverage). If it didn't, stop;
   do not commit a red tree.
5. **Commit** via HEREDOC so formatting is preserved:
   ```
   git commit -m "$(cat <<'EOF'
   <type>(<scope>): <summary>

   WHY:
     ...
   EOF
   )"
   ```
6. **Verify** — `git log --oneline -1` and `git status` to confirm a clean commit.

## Rules
- Only commit when the user has asked. Never amend a previous commit unless asked.
- If a pre-commit/CI hook fails, fix the cause and make a NEW commit — never `--no-verify`.
- Summary line ≤ 72 chars, imperative mood.
- Append the Co-Authored-By trailer only if the user's workflow uses it.

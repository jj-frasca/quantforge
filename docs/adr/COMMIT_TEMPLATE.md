# Commit Message Template

Every commit body follows this structure (CLAUDE.md rule 3). The `commit-writer` skill
populates it from the staged diff.

```
<type>(<scope>): <imperative summary ≤72 chars>

WHY:
  <1–3 sentences: the reason this exists>

WHAT:
  - <what changed>

TESTS:
  - test_<name>: <what it validates>

EDGE CASES:
  - <explicit edge cases tested>

ADR: ADR-XXX  (only when this commit enacts an architecture decision)
```

## `type`
| type | use for |
|---|---|
| `feat` | a wholly new feature/capability |
| `fix` | a bug fix |
| `refactor` | behavior-preserving restructure |
| `test` | tests only |
| `docs` | docs / ADRs / context / agent specs |
| `chore` | scaffolding, deps, config, housekeeping |
| `infra` | docker, Makefile, environment |
| `ci` | CI/CD workflows |

## `scope`
The subsystem: `data`, `research`, `validation`, `api`, `frontend`, `adr`, `claude`,
`scaffold`, `config`, `repo`, `diagrams`, etc.

## Rules
- Summary line is imperative ("add", not "added"/"adds"), ≤ 72 chars.
- `WHY` is the reason, not a restatement of the diff. Focus on intent.
- Sections that don't apply (e.g. `TESTS` on a pure-docs commit) may be omitted.
- `ADR:` appears only when the commit enacts a decision recorded in `docs/adr/`.
- Production code and its tests are committed together — never separately.

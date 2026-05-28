## Session: Implement [COMPONENT NAME]

**Phase**: [Phase number and name]
**Agent to invoke**: [data-engineer | research-expert | none]
**Cold memory to read first**: [.claude/context/FILE.md | none]

**Entry criteria** (confirm before starting):
- [ ] [What must exist before this starts — prior component, test, ADR]
- [ ] All previous session tests passing (make test)
- [ ] Coverage gate still met (make coverage)

**Today's task** (one logical unit only):
Implement [COMPONENT NAME] in [FILE PATH].

[2–4 sentences: what it does, what interface it implements, key constraints]

**Files to read first**:
- [specific file path that defines the interface this implements]
- [specific file path that this component will depend on]

**Start in plan mode**: read the above files, propose implementation plan,
wait for approval before writing any code.

**Verification**:
Run: make test
Expected: all tests pass including new ones for [COMPONENT NAME]
Run: make coverage
Expected: coverage at or above gate

**Exit criteria** (all must be true before committing):
- [ ] All tests passing
- [ ] New tests cover: happy path, edge cases, error paths
- [ ] Hypothesis property test added (if financial calculation)
- [ ] Coverage gate met
- [ ] Docstring has Notes: section explaining non-obvious decisions
- [ ] Commit follows COMMIT_TEMPLATE.md

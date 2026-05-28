## Session: Implement [VALIDATOR NAME]

**Agent to invoke**: research-expert
**Cold memory to read first**: .claude/context/validation-methodology.md,
  .claude/context/research-papers.md

**Entry criteria**:
- [ ] [dependent component] exists and has passing tests
- [ ] ValidationReport Pydantic model exists

**Today's task**:
Implement [VALIDATOR NAME] in backend/app/validation/[name].py.

Research basis: [cite the paper that defines this methodology]
Mathematical invariant: [state the invariant this component must satisfy]

**Start in plan mode**: read validation-methodology.md section for this component,
the primary research paper, existing validation components for patterns.

**Exit criteria**:
- [ ] Primary paper cited in module docstring and Notes: sections
- [ ] Mathematical invariant encoded as Hypothesis property test
- [ ] Hypothesis test runs and confirms invariant holds
- [ ] Integration test: component produces valid ValidationReport
- [ ] Commit follows COMMIT_TEMPLATE.md with ADR reference if new pattern

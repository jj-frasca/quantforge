## Session: Implement [STRATEGY NAME] Strategy

**Agent to invoke**: research-expert
**Cold memory to read first**: .claude/context/backtesting-spec.md,
  .claude/context/research-papers.md

**Entry criteria**:
- [ ] BaseStrategy ABC exists and has passing tests
- [ ] BacktestEngine exists and has passing tests
- [ ] BenchmarkComparator exists
- [ ] All previous tests passing

**Today's task**:
Implement [STRATEGY NAME] in backend/app/research/strategies/[name].py.

Research citation: [AUTHOR, YEAR, JOURNAL, DOI/SSRN — look this up before starting]
Signal logic: [describe the signal generation rule]
Parameters: [list parameters with ranges and defaults]

**Start in plan mode**: read BaseStrategy, one existing strategy for pattern,
the research paper citation. Propose implementation before writing code.

**Exit criteria**:
- [ ] Implements BaseStrategy fully (all abstract methods)
- [ ] research_citations is non-empty with real citation
- [ ] Signals always in [-1.0, 1.0] — Hypothesis property test present
- [ ] No look-ahead bias — verify by checking signal uses only past data
- [ ] BacktestEngine can run this strategy end-to-end
- [ ] Commit follows COMMIT_TEMPLATE.md

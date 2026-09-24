# FINDING-060: The About page's "scope honesty" section contradicted the current constitution

- **Severity:** Medium
- **Status:** Resolved (docs-only, no ADR — content correction, not an architecture decision)
- **Found:** 2026-09-24, autonomous session 106 (cold-directory audit of
  `frontend/src/features/about/`, cold since 2026-08-20)
- **Affects:** `AboutPage.tsx`, specifically the `aria-label="scope honesty"` section

## Finding

`AboutPage.tsx`'s "What this is NOT" section — whose entire purpose is honest, accurate scope
communication — made two claims that are false as of the current project constitution:

1. **"There is no live order routing, no broker integration, no paper trading. Out of scope by
   ADR-001."** ADR-019 (2026-07-02) explicitly **supersedes** ADR-001's "no paper trading" scope
   cut: "Add a forward-testing / paper-trading subsystem." This is not a future plan — it is a
   currently-running system (`scripts/paper.py`, `scripts/paper_broker.py`, `paper-forward.yml` /
   `paper-broker.yml` scheduled workflows, an Alpaca paper-only broker integration, ADR-020/021,
   `data/paper_portfolio.json` / `data/equity_curve.json` accruing daily). `CLAUDE.md` rule 7
   states this plainly: "Paper trading is IN scope for forward-testing (ADR-019 — paper only, NO
   real-money orders)." The About page directly contradicted the project's own current
   constitution.
2. **"Pairs and cross-sectional strategies are a future direction, not a current capability."**
   `app/research/cross_sectional/` (ADR-024/025) ranks the whole universe each period into
   dollar-neutral long/short legs, judged by the same gate as single-symbol strategies, with its
   own forward-testing and lifecycle book — a currently-running capability
   (`cross_sectional_hunt.py`, `cross-sectional-hunt.yml`, `data/cross_sectional_pool.json`, 14
   cross-sectional factors as of session 94/95). `docs/ARCHITECTURE.md`'s own current build-status
   section already states this. Only true *pairs trading* (a specific two-symbol spread) remains
   unimplemented.

Separately, the same page's "Stack" section named specific coverage percentages ("currently 100% /
~90%") that no longer match: backend coverage has read 98.5-98.8% across every session in
`RUNNING_STATE.md` for weeks, frontend read 97.03% this session — neither is "100%" or "~90%".

All three claims trace to the same root cause as `OnboardingBanner`'s stale "Eleven built-in
setups" (session 106, same session, `ca7da0a6`) and `ARCHITECTURE.md`'s own former "34 strategies,
not 11" correction: user-facing copy that names a specific fact (a count, a percentage, a scope
boundary) drifts silently once the underlying reality moves on, because nothing re-checks static
prose against the code/ADRs it describes.

## Correction

- "Not a trading app" → "Not a real-money trading app," naming what IS true now (Alpaca paper
  account, real market data, no real money — ADR-019/020/021) instead of the false blanket denial,
  while keeping what's still actually out of scope (live routing to a real brokerage account,
  WebSocket/order-book/HFT microstructure, ADR-001).
- "Not multi-asset" → "Not pairs trading," correctly scoping the true remaining gap (a specific
  two-symbol spread) instead of denying cross-sectional's existence, and naming what cross-sectional
  actually does.
- Stack coverage line: dropped the specific stale percentages for "both comfortably cleared in
  CI" — evergreen, matches the same fix pattern used for `OnboardingBanner`'s strategy count.

No ADR: this is a content correction to match already-decided, already-superseding ADRs
(ADR-019/024/025), not a new architecture decision.

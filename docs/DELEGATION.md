# QuantForge — Parallel Work Breakdown (for multiple agents on separate worktrees)

**Purpose:** hand each work package (WP) below to a *separate* agent on its *own* git worktree.
Each WP is self-contained — goal, files it OWNS, the contract with the rest of the system, tests,
acceptance criteria, and gotchas — so a fresh agent can start cold. Front-loaded on purpose.

**Read first (every agent, in order):**
1. `~/claude-work/quantforge/.claude/RUNNING_STATE.md` — the running ledger of what exists.
2. `CLAUDE.md` — the constitution (rules 1–9). **Non-negotiable:** TDD (test fails first), one
   logical unit per commit, commit body follows `docs/adr/COMMIT_TEMPLATE.md`, **ADR before any
   non-trivial architecture** (`docs/adr/`), coverage must not drop (backend 100% in practice),
   `make check` before every backend commit, `make frontend-check` before frontend commits.
3. `docs/adr/` — ADR-001..020 are the decision history. Your WP may require a NEW ADR (noted below).
4. `.claude/rules/` — backend-python, frontend-typescript, test-files conventions.

**Environment:** a local `pre-commit` hook is installed (auto-fixes EOF/whitespace/format). Push
every commit to `origin master` (granular). Verify BOTH CI + pre-commit green after each push
(`gh run list`). Live/network tests are `@pytest.mark.live` (excluded from CI). Secrets live in
gitignored `backend/.env` (Alpaca keys already there); GitHub Actions secrets already set
(ALPACA_API_KEY/SECRET, SLACK_WEBHOOK_URL).

---

## The mission (north star)
Mass-test trading strategies across many stocks → **auto-promote winners** → **paper-trade them
on Alpaca** with a **managed lifecycle** (monitor daily, **auto-exit** losers) → prove real,
out-of-time alpha → eventually manage real money. Combine the algo strategies with a **value
research engine** (genuinely undervalued companies). Everything runs **autonomously and
token-free** (pure Python on cron/GitHub Actions); a **dashboard** shows it all.

## What already exists (don't rebuild)
- **The lab** (`backend/app/research/lab/`): `holdout` (type-enforced no-peek split), `gate`
  (DSR/PBO/stability/MinTRL + **beats-buy-and-hold** graduation gate, versioned `GateConfig`),
  `experiment` (trial-counted research pool, `JsonFileExperimentStore`), `search.run_search`
  (per-symbol hunt w/ coarse-to-fine refine), `universe.run_universe_hunt` + `rank_experiments`
  (cross-symbol leaderboard + **universe-level deflation**).
- **Paper trading** (`backend/app/research/lab/paper.py`, ADR-019/020): `PaperPosition`
  (with lifecycle: `status`/`closed_at`/`exit_reasons`), `evaluate_forward` (out-of-sample
  forward score vs buy-and-hold), `freeze_graduate`, `JsonFilePaperPortfolio`, **and the lifecycle
  exit engine** `ExitPolicy` + `lifecycle_from_returns` + `evaluate_lifecycle`.
- **Data**: `YFinanceAdapter`, `AlpacaDataAdapter` (daily bars; `build_data_adapter(settings)`
  prefers Alpaca when keyed), `SecEdgarFundamentalsSource` + `FundamentalSnapshot` + fundamentals
  screen. `DataSourceAdapter` base + `OHLCVNormalizer` + `PriceBar`.
- **Autonomy**: `backend/scripts/paper.py` (forward accrual CLI), `backend/scripts/run_hunt.py`
  (universe hunt CLI), local launchd + `.github/workflows/paper-forward.yml` (daily cloud accrual).
- **Frozen paper positions**: CRM + LOW in `data/paper_portfolio.json`. Research pool in
  `data/research_pool.json`.

## Coordination — shared files (edit carefully, tiny append-only diffs; expect to rebase)
`backend/app/main.py` (router registration), `frontend/src/App.tsx` (nav), `CLAUDE.md`,
`docs/ARCHITECTURE.md` §0.6, `.claude/context/api-contracts.md`, `.env.example`. **Everything
else is partitioned by module so worktrees don't collide.**

---

## WP-A — Portfolio manager loop  ✅ DONE by base agent (2026-07-07)
`backend/app/research/lab/portfolio_manager.py::manage_portfolio(positions, graduate_experiments,
frame_provider, *, exit_policy, now)` — PROMOTES unheld graduates, MONITORS + EXITS open positions
via the ADR-020 lifecycle; cut names aren't re-promoted; closed positions kept. Wired into
`scripts/paper.py` (the daily managed step). 100% covered. WP-F builds on this.
**Also fixed:** `AlpacaDataAdapter` now requests `feed=iex` (free tier; default sip → 403).

## WP-B — Real Alpaca paper execution (broker)   [needs ADR-021]
**Goal:** submit real paper orders to Alpaca (`https://paper-api.alpaca.markets/v2`) so P&L shows
in the Alpaca dashboard; reconcile held positions to targets derived from each OPEN
`PaperPosition`'s current signal.
**Owns (new tree, no collisions):** `backend/app/execution/alpaca_broker.py`,
`backend/app/execution/sizing.py`, `backend/tests/unit/test_alpaca_broker.py`,
`backend/tests/unit/test_sizing.py`. **New ADR-021** (write first).
**Contract:** `AlpacaBroker(base_url, api_key, secret_key, *, fetcher=None)` — HTTP glue isolated
in a `# pragma: no cover` injectable method (COPY the pattern from `app/data/sources/alpaca.py` /
`edgar.py`). Methods: `account()`, `positions()`, `submit_order(symbol, qty, side)` returning typed
frozen pydantic models. `sizing.equal_weight_targets(open_positions, equity)` → target dollar/qty
per name. A `reconcile(broker, targets)` that diffs current vs target and places orders.
**Reads (do not modify):** `PaperPosition` (paper.py), `build_strategy_from_dict`, the engine (to
get the latest signal per position). Keys from `Settings` (already added: `alpaca_api_key`,
`alpaca_secret_key`). Paper endpoint differs from the DATA endpoint — use `paper-api.alpaca.markets`.
**Tests:** fake fetcher → account/positions/submit map correctly; equal-weight sizing math;
reconcile places the right diff orders; `@pytest.mark.live` smoke against the paper account.
**Acceptance:** `make check` 100%; a live smoke can place + see a paper order (local only).
**Gotchas:** signal→position (long/flat/short; strategies output position in [-1,1]); idempotent
reconcile (don't double-order); paper only, NEVER a real-money endpoint.

## WP-C — Value research engine (undervalued companies)   [needs ADR-022]
**Goal:** score how *undervalued* a company is and combine it with the algo (a value filter/signal
for the universe). This is Joe's "combine algo trading with truly undervalued companies."
**Owns (new tree):** `backend/app/research/valuation/{__init__,multiples,intrinsic_value,score}.py`,
`backend/tests/unit/test_valuation_*.py`. **New ADR-022** (write first). May extend
`SecEdgarFundamentalsSource` to pull a *history* of line items (revenue, net income, shares, equity)
— add methods, don't break existing `fetch`.
**Contract:** `UndervaluationScore` (pydantic frozen, cited): margin_of_safety, pe/ps/ev_ebitda vs
own-history percentile, a simple DCF intrinsic value vs price. `score_valuation(fundamentals_history,
price) -> UndervaluationScore`. Keep it HONEST (rule 6: "flags potential", cite the filing).
**Reads:** `app/data/fundamentals.py`, `app/data/sources/edgar.py`. **Independent** of WP-A/B/D.
**Tests:** DCF + multiples math on fixtures (no network); percentile-vs-history; margin-of-safety;
`@live` EDGAR pull. **Acceptance:** `make check` 100%.
**Gotchas:** peers are hard — do SELF-HISTORY + absolute intrinsic value FIRST; defer peer sets.
P/E over time needs price history joined with EDGAR EPS. Don't overclaim precision.

## WP-D — Backend read API for the dashboard   [no new ADR; follows api-contracts.md]
**Goal:** read-only endpoints so the frontend can show the lab + paper book.
**Owns:** `backend/app/api/v1/lab.py`, `backend/tests/integration/test_lab_endpoints.py`; small
append to `app/main.py` (register router) + `.claude/context/api-contracts.md`.
**Contract:** `GET /api/v1/leaderboard` → cross-symbol rows from `data/research_pool.json` (reuse
`rank_experiments`); `GET /api/v1/paper-portfolio` → `data/paper_portfolio.json` positions + scores
+ lifecycle. Response = typed pydantic; pool/portfolio **paths from a small helper** (default the
in-repo `data/` dir; make it injectable/overridable for tests). Read-only, sync `def` routes.
**Reads:** `Experiment`, `PaperPosition`, `rank_experiments`, the JSON stores.
**Tests:** endpoints return the shaped data from a temp pool/portfolio (dependency-override the
paths); empty files → empty lists. **Acceptance:** `make check` 100%.
**Gotchas:** don't couple to a running hunt; just read the committed JSON. Keep it stateless.

## WP-E — Monitoring dashboard (frontend)   [contract = WP-D; can start mocked]
**Goal:** a "Live" / "Lab" dashboard page: the leaderboard table + the paper portfolio (each
position: symbol, strategy, forward Sharpe vs B&H, status open/closed, exit reasons, equity curve).
**Owns:** `frontend/src/features/lab/` (page + components + tests), `frontend/src/types/lab.ts`
(Zod), `frontend/src/services/lab.ts` (fetch); small append to `frontend/src/App.tsx` (nav tab).
**Contract:** consumes WP-D's two endpoints. **Start in parallel** by mocking them with MSW against
the WP-D response shapes below; integrate when WP-D lands.
**Conventions (rules/frontend-typescript.md):** Zod at the boundary, Tanstack Query (one hook per
endpoint, handle loading/empty/error), Recharts for curves, Vitest + RTL + MSW, coverage ≥75%,
strict TS (no `any`). **Tests:** renders leaderboard + portfolio; open vs closed styling; empty
state. **Acceptance:** `make frontend-check` green. **Gotchas:** don't re-validate backend-owned
constraints (feedback-frontend-shadow-validators); assert on what the user sees.

## WP-F — Scheduled mass-testing + auto-promotion (cloud)   [depends on WP-A]
**Goal:** run the hunt on a big universe on a schedule and auto-promote graduates into the managed
book (WP-A) — the hands-off "mass test to find winners" loop.
**Owns:** `backend/scripts/cron_hunt.sh`, `.github/workflows/hunt.yml`,
`data/universes/sp500.txt` (bigger universe); wires `run_universe_hunt` + the WP-A manager.
**Contract:** scheduled (weekly) cloud job: run hunt → new graduates auto-frozen as OPEN positions
→ commit pool + portfolio. Uses Alpaca data in cloud. **Depends on WP-A** (promotion path).
**Tests:** the promotion wiring is unit-tested via WP-A; the workflow is ops (no unit test, like
the other scripts). **Acceptance:** a manual `workflow_dispatch` run is green. **Gotchas:** GitHub
Actions job time limits (chunk the universe or raise timeout); commit large JSON with a trailing
newline (store already does this). **DATA SOURCE TENSION:** the hunt needs 15–20yr history for
MinTRL → **use yfinance for the hunt** (Alpaca's free IEX feed only goes back a few years). Alpaca
is for the recent-only forward/paper loop. So WP-F's hunt should force `YFinanceAdapter()` (not
`build_data_adapter`), and accept yfinance's cloud flakiness (retry) OR run the hunt on the local
cron where yfinance is reliable, and only the paper loop in the cloud.

---

## Suggested parallelization (day 1)
- Agent 1 → **WP-B** (Alpaca execution). Agent 2 → **WP-C** (valuation). Agent 3 → **WP-D**
  (read API). Agent 4 → **WP-E** (frontend, mocked). Agent 5 → **WP-F** (after WP-A merges).
- WP-A is done by the base agent; WP-F builds on it. WP-E integrates once WP-D's contract merges.
- Each agent: write its ADR first (B, C), TDD, `make check`/`make frontend-check`, push granular,
  verify CI+pre-commit. Rebase on `master` before opening a PR to reduce shared-file conflicts.

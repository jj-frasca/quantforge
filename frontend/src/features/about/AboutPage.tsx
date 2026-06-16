import { groupByCategory } from '../strategies/groupByCategory'
import { useStrategies } from '../strategies/useStrategies'

const REPO_URL = 'https://github.com/jj-frasca/quantforge'
const adr = (n: string, label: string) => ({
  href: `${REPO_URL}/blob/master/docs/adr/ADR-${n}.md`,
  label,
})

const ADR_LINKS = [
  adr('001-monorepo-and-scope', 'ADR-001 — Monorepo + scope (no live execution)'),
  adr('007-vectorized-backtesting', 'ADR-007 — Vectorized pandas/numpy backtester (not vectorbt)'),
  adr('008-validation-first', 'ADR-008 — Validation-first methodology'),
  adr('009-storage-access-pattern', 'ADR-009 — Sync stack on psycopg3'),
  adr('010-strategy-catalog', 'ADR-010 — Schema-driven strategy catalog'),
]

export function AboutPage() {
  const strategies = useStrategies()
  const groups = strategies.data ? groupByCategory(strategies.data) : []

  return (
    <section aria-label="about page" className="page about-page">
      <header>
        <h2>About QuantForge</h2>
        <p>
          An AI-native quantitative research platform — research infrastructure, not a
          trading app. The value is methodological rigor (PBO, Deflated Sharpe,
          walk-forward, purged CV), not alpha. Every strategy in the catalog cites its
          paper; every validation metric ships with its threshold rationale.
        </p>
      </header>

      <section aria-label="what you can do" className="about-block">
        <h3>What you can do here</h3>
        <dl className="about-grid">
          <div>
            <dt>Data Explorer</dt>
            <dd>
              Fetch price bars for a symbol + range via yfinance, run the 6-check data
              quality engine, and inspect the cached series on a price chart. Bars are
              stored in TimescaleDB and served from there on subsequent runs (cache-aside).
            </dd>
          </div>
          <div>
            <dt>Backtest Results</dt>
            <dd>
              Pick a strategy and its parameters, override the engine's{' '}
              <code>initial_capital</code> and <code>cost_rate</code> if you want to see
              how costs reshape the equity curve, and run a single backtest. Returns an
              equity curve with buy-and-hold overlay and trade markers, an underwater
              drawdown plot, a rolling Sharpe, and a daily-return distribution
              histogram (skew + excess kurtosis).
            </dd>
          </div>
          <div>
            <dt>Validation Report</dt>
            <dd>
              Same strategy + range, but the engine runs an auto-generated parameter grid
              and applies the full statistical suite — PBO, Deflated Sharpe, walk-forward,
              purged CV, parameter stability. Returns a verdict plus a plain-English
              interpretation of each headline metric.
            </dd>
          </div>
        </dl>
      </section>

      <section aria-label="strategy catalog" className="about-block">
        <h3>Strategies in the catalog</h3>
        <p>
          Every strategy is a single backend file plus a catalog entry; the frontend
          renders the form fields from that catalog automatically (
          <a href={ADR_LINKS[4].href} target="_blank" rel="noreferrer">
            ADR-010
          </a>
          ). Citations are the paper / book the implementation references — implementation
          notes live in <code>.claude/context/research-papers.md</code>.
        </p>
        {strategies.isError && (
          <p role="alert">Could not load the catalog — refresh to retry.</p>
        )}
        {!strategies.data && !strategies.isError && <p>Loading catalog…</p>}
        {groups.length > 0 && (
          <div className="strategy-groups">
            {groups.map(({ category, entries }) => (
              <div key={category} className="strategy-group">
                <h4>{category}</h4>
                <ul>
                  {entries.map((entry) => (
                    <li key={entry.name} className="strategy-entry">
                      <strong>{entry.label}</strong>
                      <p className="strategy-summary">{entry.summary}</p>
                      <p>{entry.description}</p>
                      {entry.citations.length > 0 && (
                        <ul className="citations">
                          {entry.citations.map((c) => (
                            <li key={c}>{c}</li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>

      <section aria-label="validation methodology" className="about-block">
        <h3>Validation methodology</h3>
        <dl className="about-grid">
          <div>
            <dt>PBO (Probability of Backtest Overfitting)</dt>
            <dd>
              Via Combinatorially-Symmetric Cross-Validation (Bailey, Borwein, López de
              Prado, Zhu 2015). For each split of the configuration grid, check whether
              the in-sample best underperforms the out-of-sample median; PBO is the
              fraction of splits where that happens. A random strategy yields ≈ 0.5;
              we flag ≥ 0.5 as "high overfitting risk".
            </dd>
          </div>
          <div>
            <dt>Deflated Sharpe Ratio (DSR)</dt>
            <dd>
              Bailey & López de Prado (2014). The observed Sharpe deflated by the
              multiple-testing penalty for the number of configurations tried. DSR ≤ 0
              means the observed Sharpe is plausibly explained by luck given the search
              effort; DSR &gt; 0 is the "survives multiple testing" threshold.
            </dd>
          </div>
          <div>
            <dt>Walk-forward + Purged K-Fold CV</dt>
            <dd>
              López de Prado (2018), <em>Advances in Financial Machine Learning</em>. Purged
              CV removes training samples whose labels overlap the test set and applies
              an embargo after each test fold to prevent look-ahead leakage. Walk-forward
              expands the training window through time and never uses future data.
            </dd>
          </div>
          <div>
            <dt>Parameter stability</dt>
            <dd>
              How sensitive the result is to small parameter perturbations. Low stability
              means the configuration sits on a knife edge — a textbook sign of overfitting
              even when PBO and DSR look acceptable.
            </dd>
          </div>
        </dl>
      </section>

      <section aria-label="key decisions" className="about-block">
        <h3>Why it's built this way</h3>
        <p>
          Architecture decisions are recorded as ADRs. Open ones to see the options I
          considered and what tipped the call:
        </p>
        <ul className="adr-list">
          {ADR_LINKS.map((link) => (
            <li key={link.href}>
              <a href={link.href} target="_blank" rel="noreferrer">
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section aria-label="stack" className="about-block">
        <h3>Stack</h3>
        <p>
          <strong>Backend:</strong> Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync,
          psycopg3), TimescaleDB, Alembic. <strong>Research:</strong> NumPy, SciPy, pandas
          — vectorized backtesting on pandas/numpy (ADR-007 — vectorbt rejected: fails to
          build on Python 3.12). <strong>Frontend:</strong> React 19 + TypeScript strict,
          Vite, Tanstack Query 5, Zod 4, Recharts 3. <strong>Testing:</strong> pytest +
          Hypothesis (backend); Vitest + React Testing Library + MSW (frontend); coverage
          gates 85% backend / 75% frontend, currently 100% / ~90%. <strong>Tooling:</strong>{' '}
          uv, ruff, mypy strict, pre-commit, GitHub Actions CI.
        </p>
      </section>

      <section aria-label="scope honesty" className="about-block">
        <h3>What this is NOT</h3>
        <ul className="scope-list">
          <li>
            <strong>Not a trading app.</strong> There is no live order routing, no broker
            integration, no paper trading. Out of scope by ADR-001.
          </li>
          <li>
            <strong>Not an alpha generator.</strong> Strategies in the catalog are
            textbook implementations of well-cited methods, included to demonstrate that
            the rigor (PBO, DSR, purged CV) is calibrated honestly — a random walk gives
            PBO ≈ 0.5 and the engine reports it as such.
          </li>
          <li>
            <strong>Not multi-asset.</strong> The backtest engine works on a single
            symbol's close series at a time. Pairs and cross-sectional strategies are a
            future direction, not a current capability.
          </li>
        </ul>
      </section>
    </section>
  )
}

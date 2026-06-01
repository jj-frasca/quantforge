import type { IngestResponse } from '../../types/ingest'

interface Props {
  result: IngestResponse
}

// Renders the IngestResponse with the quality verdict surfaced first (honesty: a failing
// gate is the most important fact). Errors come first in the issues list, then warnings,
// then info — same prioritization the DataQualityEngine uses.
export function IngestResultView({ result }: Props) {
  const { quality_report: report } = result
  const issues = [...report.issues].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity],
  )

  return (
    <section
      aria-label="ingest result"
      className={result.stored ? 'ingest stored' : 'ingest unstored'}
    >
      <h2>{result.symbol}</h2>
      <p role="status" className="verdict">
        {result.stored
          ? `Stored ${result.bars_ingested} bars`
          : `Not stored (${result.bars_ingested} bars fetched; quality gate failed)`}
      </p>

      <dl className="metrics">
        <div>
          <dt>Bars ingested</dt>
          <dd>{result.bars_ingested}</dd>
        </div>
        <div>
          <dt>Stored to repository</dt>
          <dd>{result.stored ? 'yes' : 'no'}</dd>
        </div>
        <div>
          <dt>Quality gate</dt>
          <dd>{report.passed ? 'passed' : 'failed'}</dd>
        </div>
        <div>
          <dt>Checked at</dt>
          <dd>{report.checked_at}</dd>
        </div>
      </dl>

      {issues.length > 0 ? (
        <ul aria-label="quality issues" className="issues">
          {issues.map((issue) => (
            <li key={`${issue.check}-${issue.message}`} className={`issue ${issue.severity}`}>
              <span className="check">{issue.check}</span>
              <span className="severity">[{issue.severity}]</span>
              <span className="message">{issue.message}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="no-issues">No data-quality issues flagged.</p>
      )}
    </section>
  )
}

const severityOrder = { error: 0, warning: 1, info: 2 } as const

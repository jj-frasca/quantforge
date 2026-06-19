import type { CompareRow } from './useCompareBacktests'

interface Props {
  results: CompareRow[]
}

// Threshold above which the parameter-sensitivity framing earns its place on
// screen. Picked qualitatively: a 0.5 swing in Sharpe across configs of the same
// strategy is a strong "different configs are not telling the same story" signal
// and is exactly the kind of in-sample variance PBO+DSR are built to penalize.
const WIDE_SPREAD = 0.5

const fmt = (value: number): string => value.toFixed(2)

// Surfaces the min/max Sharpe across the successful comparison rows + the spread
// between them. For wide spreads, prints a one-line callout naming the framing
// the Validation page actually answers ("parameter sensitivity"). For 0–1
// success rows there's nothing to interpret — the component renders nothing
// rather than print a misleading "spread: 0.00" line.
export function CompareSpreadCallout({ results }: Props) {
  const sharpes = results
    .filter((r): r is Extract<CompareRow, { status: 'success' }> => r.status === 'success')
    .map((r) => r.data.metrics.sharpe)
  if (sharpes.length < 2) return null

  const min = Math.min(...sharpes)
  const max = Math.max(...sharpes)
  const spread = max - min
  const isWide = spread >= WIDE_SPREAD

  return (
    <section
      role="region"
      aria-label="Sharpe spread"
      className={`compare-spread-callout${isWide ? ' wide' : ''}`}
    >
      <strong>Sharpe spread: {fmt(spread)}</strong>{' '}
      <span>
        ({fmt(min)} → {fmt(max)} across {sharpes.length} configs)
      </span>
      {isWide && (
        <p className="compare-spread-flag">
          High parameter sensitivity — small param changes shift the Sharpe by a
          large amount. Validate the best-looking config to see whether the gap
          is signal or overfitting.
        </p>
      )}
    </section>
  )
}

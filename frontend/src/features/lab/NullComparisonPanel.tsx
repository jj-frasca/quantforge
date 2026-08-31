import type { NullComparison } from '../../types/lab'

const asSharpe = (value: number): string => (value >= 0 ? `+${value.toFixed(3)}` : value.toFixed(3))

const EXCESS_STATISTIC = 'walk-forward excess'

// ADR-051/064/068. The leaderboard says what the search found; this says whether what it found is
// distinguishable from what the same search finds on data with NO EDGE by construction. The verdict
// is computed by the backend and rendered here verbatim — never re-derived from the numbers.
// ADR-072: the band has two edges. `real_below_null_p5` is only ever set on the centered excess
// row, where zero means the same thing on both sides, so a real median under the null is a result
// rather than a statement about drift.
export function NullComparisonPanel({ comparisons }: { comparisons: NullComparison[] }) {
  if (comparisons.length === 0) {
    return null
  }
  const hasExcess = comparisons.some((c) => c.statistic === EXCESS_STATISTIC)

  return (
    <section aria-label="null comparison" className="deflation-headline">
      <h3>The search against a no-edge surrogate</h3>
      <table>
        <caption>
          The pool&apos;s out-of-sample diagnostics beside the same statistic measured on symbols
          with no edge by construction, on the subset whose history matches the null&apos;s
        </caption>
        <thead>
          <tr>
            <th scope="col">Statistic</th>
            <th scope="col">Null model</th>
            <th scope="col">Real median</th>
            <th scope="col">Matched sample</th>
            <th scope="col">Null median</th>
            <th scope="col">Null p5</th>
            <th scope="col">Null p95</th>
            <th scope="col">Verdict</th>
          </tr>
        </thead>
        <tbody>
          {comparisons.map((c) => (
            <tr key={`${c.statistic}-${c.null_mode}-${c.matched_n_bars ?? 'any'}`}>
              <td>{c.statistic}</td>
              <td>{c.null_mode}</td>
              <td>{asSharpe(c.real_median)}</td>
              <td>
                {c.matched_n.toLocaleString('en-US')}
                {c.matched_n_bars === null
                  ? ''
                  : ` @ ${c.matched_n_bars.toLocaleString('en-US')} bars`}
              </td>
              <td>{asSharpe(c.null_median)}</td>
              <td>{asSharpe(c.null_p5)}</td>
              <td>{asSharpe(c.null_p95)}</td>
              <td>
                {!c.comparable ? (
                  <>
                    Not comparable — <span>{c.mismatch}</span>
                  </>
                ) : c.real_exceeds_null_p95 ? (
                  'Separates'
                ) : c.real_below_null_p5 ? (
                  'Separates below — the search subtracts'
                ) : (
                  'Does not separate'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {comparisons.map((c) =>
        c.difference_ci_low === null || c.difference_ci_high === null ? null : (
          <p
            data-testid="difference-interval"
            key={`diff-${c.statistic}-${c.null_mode}-${c.matched_n_bars ?? 'any'}`}
          >
            <strong>{c.null_mode}</strong>, difference of medians{' '}
            {asSharpe(c.real_median - c.null_median)} [{asSharpe(c.difference_ci_low)},{' '}
            {asSharpe(c.difference_ci_high)}] over {c.difference_n_clusters.toLocaleString('en-US')}{' '}
            symbol clusters —{' '}
            <strong>
              {c.difference_ci_low <= 0 && c.difference_ci_high >= 0 ? 'spans zero' : 'excludes zero'}
            </strong>
            . This sizes whether the two <em>central tendencies</em> differ, which is a different
            question from the verdict above; and it is a <strong>lower bound</strong> on its own
            width, because the symbols share one calendar window.
          </p>
        ),
      )}
      {!hasExcess && (
        <p data-testid="excess-note">
          Every row above is denominated in the drift of the series it was measured on — on a null
          the finalist&apos;s Sharpe comes out at that series&apos; own buy-and-hold Sharpe. The
          drift-controlled comparison is <strong>not measured</strong> here: the pool, the null
          artifacts, or both predate the paired benchmark.
        </p>
      )}
    </section>
  )
}

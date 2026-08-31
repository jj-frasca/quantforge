import type { WindowComparison } from '../../types/lab'

const signed = (value: number): string => (value >= 0 ? `+${value.toFixed(3)}` : value.toFixed(3))
const band = (low: number, high: number): string => `[${signed(low)}, ${signed(high)}]`

// ADR-074. ADR-063's second clause asked whether the longer in-sample window degraded selection.
// The clause named the pool's median holdout Sharpe, which does not exist at a readable size — the
// gate has produced one graduate under the live family — so this reads the same question on the
// finalist, differenced within each symbol. The two rows are NOT interchangeable: the raw one is
// denominated in each window's own drift, the excess one has that removed and is the criterion.
export function WindowComparisonPanel({ comparison }: { comparison: WindowComparison }) {
  const { excess_delta_median, excess_delta_ci_low, excess_delta_ci_high } = comparison

  return (
    <section aria-label="window comparison" className="deflation-headline">
      <h3>What the longer search window did to the finalist</h3>
      <table>
        <caption>
          Each symbol&apos;s finalist differenced across the ADR-063 window change, over the{' '}
          {comparison.n_symbols.toLocaleString('en-US')} symbols searched at both{' '}
          {comparison.short_n_bars.toLocaleString('en-US')} and{' '}
          {comparison.long_n_bars.toLocaleString('en-US')} bars
        </caption>
        <thead>
          <tr>
            <th scope="col">Paired delta</th>
            <th scope="col">Median</th>
            <th scope="col">95% interval</th>
            <th scope="col">Reading</th>
          </tr>
        </thead>
        <tbody>
          <tr data-testid="excess-delta">
            <td>Walk-forward excess over buy-and-hold</td>
            {excess_delta_median === null ||
            excess_delta_ci_low === null ||
            excess_delta_ci_high === null ? (
              <td colSpan={3}>
                <strong>Not measured</strong> — the rows searched before ADR-063 predate the paired
                benchmark, so their drift cannot be removed
              </td>
            ) : (
              <>
                <td>{signed(excess_delta_median)}</td>
                <td>{band(excess_delta_ci_low, excess_delta_ci_high)}</td>
                <td>
                  The criterion (n={comparison.excess_n.toLocaleString('en-US')}) — each side net of
                  what holding it earned over the same windows
                </td>
              </>
            )}
          </tr>
          <tr>
            <td>Walk-forward out-of-sample Sharpe</td>
            <td>{signed(comparison.oos_delta_median)}</td>
            <td>{band(comparison.oos_delta_ci_low, comparison.oos_delta_ci_high)}</td>
            <td>Surrogate — each side is denominated in its own window&apos;s drift</td>
          </tr>
          <tr>
            <td>In-sample observed Sharpe</td>
            <td>{signed(comparison.in_sample_delta_median)}</td>
            <td>{band(comparison.in_sample_delta_ci_low, comparison.in_sample_delta_ci_high)}</td>
            <td>What the search saw when it chose</td>
          </tr>
        </tbody>
      </table>
      <p>
        The longer window changes which strategy the search picks on{' '}
        <strong>
          {comparison.n_finalist_changed.toLocaleString('en-US')} of{' '}
          {comparison.n_symbols.toLocaleString('en-US')}
        </strong>{' '}
        symbols.
      </p>
    </section>
  )
}

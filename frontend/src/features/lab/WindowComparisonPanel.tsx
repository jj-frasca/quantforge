import type { WindowComparison, WindowExperiment } from '../../types/lab'

const signed = (value: number): string => (value >= 0 ? `+${value.toFixed(3)}` : value.toFixed(3))
const band = (low: number, high: number): string => `[${signed(low)}, ${signed(high)}]`

// ADR-074. ADR-063's second clause asked whether the longer in-sample window degraded selection.
// The clause named the pool's median holdout Sharpe, which does not exist at a readable size — the
// gate has produced one graduate under the live family — so this reads the same question on the
// finalist, differenced within each symbol. The two rows are NOT interchangeable: the raw one is
// denominated in each window's own drift, the excess one has that removed and is the criterion.
export function WindowComparisonPanel({
  comparison,
  experiment,
}: {
  comparison: WindowComparison
  experiment?: WindowExperiment | null
}) {
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
                <strong>Not measured</strong> here — the pool&apos;s pre-ADR-063 rows predate the
                paired benchmark, so their drift cannot be removed, and nothing in the daily
                discovery will ever fill this in. It was measured instead by the pre-registered
                experiment below (ADR-076).
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
      <FrozenExperiment experiment={experiment ?? null} />
    </section>
  )
}

// ADR-077. This block is deliberately NOT a row in the table above. It is over its own frozen
// sample and read at its own alpha, and a band of one kind rendered beside three of the other is a
// wrong comparison presented as a right one.
function FrozenExperiment({ experiment }: { experiment: WindowExperiment | null }) {
  if (experiment === null) {
    return (
      <p data-testid="window-experiment">
        The pre-registered experiment (ADR-076) <strong>has not been run</strong> in this checkout,
        so the drift-controlled delta is unmeasured here — which is not the same claim as an effect
        of zero.
      </p>
    )
  }

  const { criterion, at_look_one_alpha, criterion_alpha, sample } = experiment
  const median = criterion.excess_delta_median
  const low = criterion.excess_delta_ci_low
  const high = criterion.excess_delta_ci_high
  if (median === null || low === null || high === null) {
    return (
      <p data-testid="window-experiment">
        The pre-registered experiment (ADR-076) ran but <strong>no symbol</strong> ended carrying
        the benchmark at both windows, so it has nothing to report.
      </p>
    )
  }

  const fires = high < 0 || low > 0
  return (
    <div data-testid="window-experiment">
      <h4>The pre-registered answer (ADR-076) — closed</h4>
      <p>
        Drift-controlled excess delta <strong>{signed(median)}</strong> {band(low, high)} over{' '}
        <strong>{sample.length.toLocaleString('en-US')}</strong> symbols frozen and committed before
        any of them was searched. The interval is at the Pocock two-look boundary,{' '}
        <strong>&alpha; = {criterion_alpha}</strong> — not 95%, so it is not comparable to the bands
        above. {fires ? 'The criterion fires.' : 'The criterion does not fire.'}
      </p>
      <p>
        Look 2 of 2: the sequence is <strong>closed</strong>. Extending the sample needs a new
        pre-registration with a three-look boundary, not another run of this one.
      </p>
      {at_look_one_alpha.excess_delta_ci_low !== null &&
        at_look_one_alpha.excess_delta_ci_high !== null && (
          <p>
            For continuity, the same estimator at the 0.05 look 1 was read at:{' '}
            {band(at_look_one_alpha.excess_delta_ci_low, at_look_one_alpha.excess_delta_ci_high)}.
          </p>
        )}
    </div>
  )
}

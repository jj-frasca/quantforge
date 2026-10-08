// GatePowerPanel: the measured POWER of the whole gate (ADR-041/042/053). The Type-I error says
// how often the gate is wrong when there is nothing there; this says how often it is right when
// there is. Showing one without the other reads conservatism as strength.
import { render, screen, within } from '@testing-library/react'

import type { PowerCell, PowerSweep } from '../../types/lab'
import { GatePowerPanel } from './GatePowerPanel'

const cell = (overrides: Partial<PowerCell> = {}): PowerCell => ({
  n_symbols: 50,
  n_detected: 32,
  detection_rate: 0.64,
  n_clear_deflation_bar: 32,
  deflation_bar: 2.11,
  edge: 'ar1',
  phi: 0.3,
  half_life: null,
  oracle_sharpes: [3.9, 3.9],
  net_oracle_sharpes: [2.9, 2.9],
  finalist_observed_sharpes: [3.0, 3.0],
  gate_pass_counts: { dsr: 44 },
  n_bars: [5400],
  capture_ratio: 0.769,
  net_capture_ratio: 1.034,
  net_capture_by_category: {},
  achievable_oracle_sharpes: [],
  achievable_capture_ratio: null,
  gate_config_version: 'v1',
  search_config_version: 'abcdef0123456789',
  ...overrides,
})

const sweep = (overrides: Partial<PowerSweep> = {}): PowerSweep => ({
  edge: 'ar1',
  gate_config_version: 'v1',
  search_config_version: 'abcdef0123456789',
  n_bars: 5400,
  cells: [cell()],
  ...overrides,
})

test('states the detection rate against the effect size that produced it', () => {
  render(<GatePowerPanel sweeps={[sweep()]} />)
  expect(screen.getByText('64%')).toBeInTheDocument()
  expect(screen.getByText('+3.90')).toBeInTheDocument()
  expect(screen.getByText('32 / 50')).toBeInTheDocument()
})

test('identifies AR(1) scores as historical reference scores without asserting optimality', () => {
  render(<GatePowerPanel sweeps={[sweep()]} />)
  expect(screen.getByRole('columnheader', { name: 'Reference Sharpe' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Reference net of costs' })).toBeInTheDocument()
  expect(screen.getByText(/historical reference sign strategy/)).toHaveTextContent(
    'omits the drift intercept',
  )
  expect(screen.getByText(/historical reference sign strategy/)).toHaveTextContent(
    'not conditional-mean optimal or realized-sample maximum Sharpes',
  )
  expect(screen.getByTestId('power-caveat')).toHaveTextContent(
    'in-sample finalist Sharpe relative to the stated reference',
  )
  expect(screen.getByTestId('power-caveat')).toHaveTextContent(
    'does not establish that no tradeable edge exists',
  )
  expect(screen.getByText('+3.90')).toBeInTheDocument()
  expect(screen.getByText('+2.90')).toBeInTheDocument()
  expect(screen.getByText('64%')).toBeInTheDocument()
  expect(screen.getByText('32 / 50')).toBeInTheDocument()
})

const bandSweep = () => sweep({
  edge: 'band_reversion',
  cells: [cell({ edge: 'band_reversion', phi: null, half_life: 5 })],
})

test('identifies historical band scores as latent and filtered references without optimality claims', () => {
  render(<GatePowerPanel sweeps={[bandSweep()]} />)
  expect(screen.getByRole('columnheader', { name: 'Latent reference Sharpe' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Latent reference net of costs' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Filtered reference Sharpe' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Capture vs filtered reference' })).toBeInTheDocument()
  expect(screen.getByText(/historical latent and filtered sign references/)).toHaveTextContent(
    'use predicted log returns while their scores use simple returns',
  )
  expect(screen.getByText(/historical latent and filtered sign references/)).toHaveTextContent(
    'do not certify an optimal strategy before or after costs, or a maximum sample Sharpe',
  )
  expect(screen.queryByText(/historical reference sign strategy/)).not.toBeInTheDocument()
  expect(screen.getByText('+3.90')).toBeInTheDocument()
  expect(screen.getByText('+2.90')).toBeInTheDocument()
  expect(screen.getByText('64%')).toBeInTheDocument()
  expect(screen.getByText('32 / 50')).toBeInTheDocument()
  expect(screen.getByText('76.9%')).toBeInTheDocument()
  expect(screen.getByText('103.4%')).toBeInTheDocument()
  expect(screen.getAllByText('—')).toHaveLength(2)
})

test('scopes drift and log-return qualifications to their own processes in mixed sweeps', () => {
  render(<GatePowerPanel sweeps={[sweep(), bandSweep()]} />)
  const tables = screen.getAllByRole('table')
  expect(within(tables[0]).getByText(/historical reference sign strategy/)).toBeInTheDocument()
  expect(within(tables[1]).queryByText(/historical reference sign strategy/)).not.toBeInTheDocument()
  expect(within(tables[0]).queryByText(/historical latent and filtered sign references/)).not.toBeInTheDocument()
  expect(within(tables[0]).getByRole('columnheader', { name: 'Reference Sharpe' })).toBeInTheDocument()
  expect(within(tables[1]).getByText(/historical latent and filtered sign references/)).toBeInTheDocument()
  expect(within(tables[1]).getByRole('columnheader', { name: 'Latent reference Sharpe' })).toBeInTheDocument()
})

test('explains information access without inferring absent recoverable edge from filtered scores', () => {
  render(<GatePowerPanel sweeps={[bandSweep()]} />)
  const caveat = screen.getByTestId('power-caveat')
  expect(caveat).toHaveTextContent('filtered reference uses prices; the latent reference knows the hidden state')
  expect(caveat).toHaveTextContent('near-zero filtered net reference does not establish that no recoverable edge exists')
  expect(caveat).not.toHaveTextContent('optimal filter')
  expect(caveat).not.toHaveTextContent('the difference is the entire edge')
})

test('labels capture as in-sample while preserving served ratios and detection rates', () => {
  render(<GatePowerPanel sweeps={[sweep(), bandSweep()]} />)
  expect(screen.getAllByRole('columnheader', { name: 'Capture (in-sample)' })).toHaveLength(2)
  expect(screen.queryByRole('columnheader', { name: 'Capture (upper bound)' })).not.toBeInTheDocument()
  expect(screen.getAllByText('64%')).toHaveLength(2)
  expect(screen.getAllByText('76.9%')).toHaveLength(2)
  expect(screen.getAllByText('103.4%')).toHaveLength(2)
})

test('does not present synthetic detection controls as bounds on real-market power', () => {
  render(<GatePowerPanel sweeps={[sweep(), bandSweep()]} />)
  const caveat = screen.getByTestId('power-caveat')
  expect(caveat).toHaveTextContent('always-on synthetic controls do not establish a bound on real-market power')
  expect(caveat).not.toHaveTextContent('upper bound')
})

test('preserves existing labels for an unknown process', () => {
  render(<GatePowerPanel sweeps={[sweep({ edge: 'future_process' })]} />)
  expect(screen.getByRole('columnheader', { name: 'Oracle Sharpe' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Oracle net of costs' })).toBeInTheDocument()
  expect(screen.queryByText(/historical latent and filtered sign references/)).not.toBeInTheDocument()
})

test('takes the middle value, not an average, when a cell has an odd number of oracle Sharpes', () => {
  // Every other fixture's Sharpe arrays have an even length (2 or 0), so median()'s
  // odd-length branch (the plain `sorted[mid]`, no averaging) had never run.
  render(
    <GatePowerPanel
      sweeps={[sweep({ cells: [cell({ oracle_sharpes: [3.9, 4.5, 3.9] })] })]}
    />,
  )
  expect(screen.getByText('+3.90')).toBeInTheDocument()
})

test('labels a band-reversion sweep by its half-life, not by phi', () => {
  render(
    <GatePowerPanel
      sweeps={[
        sweep({
          edge: 'band_reversion',
          cells: [
            cell({
              edge: 'band_reversion',
              phi: null,
              half_life: 5,
              detection_rate: 0,
              n_detected: 0,
              n_clear_deflation_bar: 0,
            }),
          ],
        }),
      ]}
    />,
  )
  expect(screen.getByText('half-life 5')).toBeInTheDocument()
  expect(screen.getByText('0%')).toBeInTheDocument()
})

test('labels a mean-reverting AR(1) sweep with a minus sign, not a bare number', () => {
  // power_calibration.py's default phi is -0.20 (mean reversion); phi > 0 is trend
  // persistence — the label's sign branch had only ever been exercised with a positive phi.
  render(
    <GatePowerPanel
      sweeps={[sweep({ cells: [cell({ phi: -0.2 })] })]}
    />,
  )
  expect(screen.getByText('phi -0.2')).toBeInTheDocument()
})

test('shows capture, because a zero with low capture is a catalog problem not a gate problem', () => {
  render(<GatePowerPanel sweeps={[sweep()]} />)
  expect(screen.getByText('76.9%')).toBeInTheDocument()
})

test('renders the capture ratios the backend computed rather than re-deriving them', () => {
  // The panel used to divide the raw Sharpe arrays itself, which is the shadow-validator pattern
  // the frontend rules forbid — and it could not have applied the backend's noise refusal.
  render(
    <GatePowerPanel
      sweeps={[
        sweep({
          cells: [
            cell({
              capture_ratio: 0.5,
              net_capture_ratio: null,
              oracle_sharpes: [9.9, 9.9],
              finalist_observed_sharpes: [9.9, 9.9],
            }),
          ],
        }),
      ]}
    />,
  )
  expect(screen.getByText('50.0%')).toBeInTheDocument()
  expect(screen.queryByText('100.0%')).not.toBeInTheDocument()
})

test('renders nothing when power has never been measured', () => {
  const { container } = render(<GatePowerPanel sweeps={[]} />)
  expect(container).toBeEmptyDOMElement()
})

test('shows capture against the oracle NET of the costs the catalog itself paid', () => {
  // ADR-055: the finalist's Sharpe is charged 10bp on turnover and the oracle's was not, so the
  // gross ratio divides two different accounting conventions. Both are shown; the net one is the
  // comparable one.
  render(<GatePowerPanel sweeps={[sweep()]} />)
  expect(screen.getByText('76.9%')).toBeInTheDocument()
  expect(screen.getByText('+2.90')).toBeInTheDocument()
  expect(screen.getByText('103.4%')).toBeInTheDocument()
})

test('a cell measured before the net oracle existed shows a dash, not a capture of zero', () => {
  render(
    <GatePowerPanel
      sweeps={[sweep({ cells: [cell({ net_oracle_sharpes: [], net_capture_ratio: null })] })]}
    />,
  )
  // Four dashes: the net oracle and its capture, plus the achievable pair an AR(1) cell never
  // records (its state IS the observed return, so no filter correction applies).
  expect(screen.getAllByText('—')).toHaveLength(4)
})

test('a net oracle that costs have eaten has no capture fraction', () => {
  // At |phi| = 0.10 the net oracle sits inside its own standard error: the backend refuses the
  // ratio, and the panel must show that refusal rather than a number.
  render(
    <GatePowerPanel
      sweeps={[
        sweep({ cells: [cell({ net_oracle_sharpes: [-0.06, 0.02], net_capture_ratio: null })] }),
      ]}
    />,
  )
  expect(screen.getAllByText('—')).toHaveLength(3)
})

test('splits capture by the kind of strategy that earned it (ADR-059)', () => {
  // On fast band reversion the overall capture is mostly a TREND strategy fitting the
  // random-walk level; the reverting row is the one that says whether anything trading the
  // planted process kept any of it. A single number cannot show that.
  render(
    <GatePowerPanel
      sweeps={[
        sweep({
          edge: 'band_reversion',
          cells: [
            cell({
              edge: 'band_reversion',
              phi: null,
              half_life: 1,
              detection_rate: 0,
              n_detected: 0,
              n_clear_deflation_bar: 0,
              net_capture_ratio: 0.316,
              net_capture_by_category: { 'Mean Reversion': 0.22, Trend: 0.316 },
            }),
          ],
        }),
      ]}
    />,
  )
  expect(screen.getByText(/Mean Reversion 22.0%/)).toBeInTheDocument()
  expect(screen.getByText(/Trend 31.6%/)).toBeInTheDocument()
})

test('says nothing about categories when a cell predates the split', () => {
  render(<GatePowerPanel sweeps={[sweep()]} />)
  expect(screen.queryByTestId('capture-by-category')).not.toBeInTheDocument()
})

test('preserves served filtered-reference scores and capture (ADR-061, FINDING-159)', () => {
  // The price-filtered reference has different information access from the latent reference.
  // FINDING-159 qualifies its optimality; neither historical score nor capture is recomputed.
  render(
    <GatePowerPanel
      sweeps={[
        sweep({
          edge: 'band_reversion',
          cells: [
            cell({
              edge: 'band_reversion',
              phi: null,
              half_life: 5,
              detection_rate: 0,
              n_detected: 0,
              n_clear_deflation_bar: 0,
              net_capture_ratio: 0.453,
              achievable_oracle_sharpes: [0.94, 0.94],
              achievable_capture_ratio: 1.07,
            }),
          ],
        }),
      ]}
    />,
  )
  expect(screen.getByText('107.0%')).toBeInTheDocument()
  expect(screen.getByText('+0.94')).toBeInTheDocument()
})

test('an AR(1) cell shows a dash for the achievable oracle, because its state is observed', () => {
  // The AR(1) driver records no filtered reference because its state is observed.
  // FINDING-155 separately qualifies the historical sign reference's drift omission.
  render(<GatePowerPanel sweeps={[sweep()]} />)
  expect(screen.getAllByText('—')).toHaveLength(2)
})

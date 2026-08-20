// GatePowerPanel: the measured POWER of the whole gate (ADR-041/042/053). The Type-I error says
// how often the gate is wrong when there is nothing there; this says how often it is right when
// there is. Showing one without the other reads conservatism as strength.
import { render, screen } from '@testing-library/react'

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
  expect(screen.getAllByText('—')).toHaveLength(2)
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
  expect(screen.getByText('—')).toBeInTheDocument()
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

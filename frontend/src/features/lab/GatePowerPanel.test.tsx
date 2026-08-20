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
  finalist_observed_sharpes: [3.0, 3.0],
  gate_pass_counts: { dsr: 44 },
  n_bars: [5400],
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

test('renders nothing when power has never been measured', () => {
  const { container } = render(<GatePowerPanel sweeps={[]} />)
  expect(container).toBeEmptyDOMElement()
})

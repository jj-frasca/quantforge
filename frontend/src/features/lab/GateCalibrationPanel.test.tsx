// GateCalibrationPanel: the measured Type-I error of the whole gate (ADR-036/037). The number a
// sceptical reader should see before any claim about a graduate.
import { render, screen } from '@testing-library/react'

import type { NullCalibration } from '../../types/lab'
import { GateCalibrationPanel } from './GateCalibrationPanel'

const calibration = (overrides: Partial<NullCalibration> = {}): NullCalibration => ({
  n_symbols: 200,
  n_graduates: 2,
  false_graduation_rate: 0.01,
  n_clear_deflation_bar: 0,
  deflation_bar: 2.11,
  max_deflated_sharpe: 0.92,
  max_holdout_sharpe: 0.85,
  holdout_years: [2.4],
  n_bars: [5400],
  walk_forward_oos_sharpes: [],
  purged_cv_oos_sharpes: [],
  gate_config_version: 'v1',
  search_config_version: 'abcdef0123456789',
  null_mode: 'iid_normal',
  ...overrides,
})

test('states the measured false-graduation rate for each null mode', () => {
  render(
    <GateCalibrationPanel
      calibrations={[calibration(), calibration({ null_mode: 'bootstrap:SPY' })]}
    />,
  )
  expect(screen.getByText('iid_normal')).toBeInTheDocument()
  expect(screen.getByText('bootstrap:SPY')).toBeInTheDocument()
  expect(screen.getAllByText('1.00%')).toHaveLength(2)
  expect(screen.getAllByText('abcdef01')).toHaveLength(2)
  expect(screen.getByRole('columnheader', { name: 'History' })).toBeInTheDocument()
  expect(screen.getAllByText('5,400')).toHaveLength(2)
})

test('keeps separate rows for the same null measured at different histories', () => {
  render(
    <GateCalibrationPanel
      calibrations={[calibration(), calibration({ n_bars: [7400] })]}
    />,
  )
  expect(screen.getByText('5,400')).toBeInTheDocument()
  expect(screen.getByText('7,400')).toBeInTheDocument()
})

test('says plainly that a positive deflated Sharpe is not sufficient on its own', () => {
  render(<GateCalibrationPanel calibrations={[calibration()]} />)
  expect(screen.getByTestId('dsr-caveat')).toHaveTextContent(/0\.92/)
  expect(screen.getByTestId('dsr-caveat')).toHaveTextContent(/not sufficient/i)
})

test('renders nothing when the gate has never been calibrated', () => {
  const { container } = render(<GateCalibrationPanel calibrations={[]} />)
  expect(container).toBeEmptyDOMElement()
})

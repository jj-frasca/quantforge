// ValidationReportView: renders the pass vs fail verdict, the metric values, and surfaces
// flags (a failing report must read clearly as "does not pass").
import { render, screen } from '@testing-library/react'

import { failingReport, passingReport } from '../../test/utils'
import { ValidationReportView } from './ValidationReportView'

test('renders a passing verdict and the metrics', () => {
  render(<ValidationReportView report={passingReport} />)
  expect(screen.getByRole('status')).toHaveTextContent(/passes validation/i)
  expect(screen.getByText('20.0%')).toBeInTheDocument() // pbo
  expect(screen.getByText('1.20')).toBeInTheDocument() // observed sharpe
  expect(screen.queryByLabelText('flags')).not.toBeInTheDocument()
})

test('renders a failing verdict and surfaces flags', () => {
  render(<ValidationReportView report={failingReport} />)
  expect(screen.getByRole('status')).toHaveTextContent(/does not pass/i)
  expect(screen.getByText('89.0%')).toBeInTheDocument() // pbo
  const flags = screen.getByLabelText('flags')
  expect(flags).toHaveTextContent(/high overfitting risk/i)
})

test('renders the interpretations panel with each metric verdict', () => {
  render(<ValidationReportView report={failingReport} />)
  const interpretations = screen.getByLabelText('interpretations')
  expect(interpretations).toHaveTextContent(/PBO 89%.*overfit/i)
  expect(interpretations).toHaveTextContent(/Deflated Sharpe.*luck/i)
  expect(interpretations).toHaveTextContent(/Parameter stability.*fragility/i)
})

// ADR-038: the walk-forward tile must report what the splits MEASURED, not how many there were.
test('reports the walk-forward out-of-sample Sharpe when one was computed', () => {
  render(
    <ValidationReportView
      report={{
        ...passingReport,
        walk_forward: {
          n_splits: 5,
          splits: [],
          mean_is_sharpe: 1.0,
          mean_oos_sharpe: 0.34,
          consistency: 0.8,
          efficiency: 0.34,
        },
      }}
    />,
  )
  expect(screen.getByText('0.34')).toBeInTheDocument()
  expect(screen.getByText(/4 of 5 windows/i)).toBeInTheDocument()
})

test('falls back to the split count when nothing walked forward', () => {
  render(<ValidationReportView report={{ ...passingReport, walk_forward: null }} />)
  expect(screen.getByText(/not measured/i)).toBeInTheDocument()
})

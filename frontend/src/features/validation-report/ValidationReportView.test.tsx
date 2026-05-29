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

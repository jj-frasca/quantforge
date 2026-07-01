// BenchmarkComparisonPanel: the strategy-vs-SPY decomposition (ADR-013). Renders nothing
// when the comparison is absent (backend returned null); when present, surfaces alpha/beta/
// IR with an honest headline — a positive-return strategy that is all beta added no value.
import { render, screen } from '@testing-library/react'

import type { BenchmarkComparison } from '../../types/backtest'
import { BenchmarkComparisonPanel } from './BenchmarkComparisonPanel'

const beatsMarket: BenchmarkComparison = {
  benchmark_symbol: 'SPY',
  alpha: 0.037,
  beta: 0.85,
  information_ratio: 0.61,
  tracking_error: 0.09,
  benchmark_relative_drawdown: -0.12,
}

const justBeta: BenchmarkComparison = {
  benchmark_symbol: 'SPY',
  alpha: -0.021,
  beta: 1.02,
  information_ratio: -0.34,
  tracking_error: 0.05,
  benchmark_relative_drawdown: -0.18,
}

// The trap browser-verification caught: a money-losing strategy that went net-short (negative
// beta) has POSITIVE CAPM alpha but NEGATIVE excess return. Keying the verdict off alpha would
// print "beat SPY" on a strategy that lost money. The verdict must key off information ratio.
const positiveAlphaButLost: BenchmarkComparison = {
  benchmark_symbol: 'SPY',
  alpha: 0.009,
  beta: -0.32,
  information_ratio: -0.42,
  tracking_error: 0.29,
  benchmark_relative_drawdown: -0.41,
}

test('renders nothing when there is no benchmark comparison', () => {
  const { container } = render(<BenchmarkComparisonPanel comparison={null} />)
  expect(container).toBeEmptyDOMElement()
})

test('surfaces alpha, beta, information ratio, tracking error, and relative drawdown', () => {
  render(<BenchmarkComparisonPanel comparison={beatsMarket} />)
  const region = screen.getByRole('region', { name: 'benchmark comparison' })
  expect(region).toBeInTheDocument()
  expect(screen.getByText('3.7%')).toBeInTheDocument() // alpha (annualized)
  expect(screen.getByText('0.85')).toBeInTheDocument() // beta
  expect(screen.getByText('0.61')).toBeInTheDocument() // information ratio
  expect(screen.getByText('9.0%')).toBeInTheDocument() // tracking error
  expect(screen.getByText('-12.0%')).toBeInTheDocument() // relative drawdown
  expect(screen.getByRole('heading', { name: /vs\. SPY/i })).toBeInTheDocument()
})

test('a positive information ratio reads as beating the benchmark', () => {
  render(<BenchmarkComparisonPanel comparison={beatsMarket} />)
  expect(screen.getByRole('status')).toHaveTextContent(/beat SPY/i)
  expect(screen.getByRole('status')).not.toHaveTextContent(/did not beat/i)
})

test('a negative information ratio is called out as not beating the benchmark', () => {
  // The honest-UI rule (rules/frontend-typescript.md): a strategy that trailed the index
  // must SAY so, not hide behind a positive headline number.
  render(<BenchmarkComparisonPanel comparison={justBeta} />)
  expect(screen.getByRole('status')).toHaveTextContent(/did not beat SPY/i)
})

test('positive alpha but negative excess return still reads as NOT beating', () => {
  // Regression for the exact case browser verification surfaced: alpha > 0 (net-short,
  // negative beta) on a strategy that actually lost money. Must not print "beat SPY".
  render(<BenchmarkComparisonPanel comparison={positiveAlphaButLost} />)
  expect(screen.getByRole('status')).toHaveTextContent(/did not beat SPY/i)
})

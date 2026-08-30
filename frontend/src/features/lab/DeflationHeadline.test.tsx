import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { DeflationHeadline } from './DeflationHeadline'
import type { PoolReport } from '../../types/lab'

const report: PoolReport = {
  n_experiments: 3208,
  n_symbols: 607,
  n_trials: 115009,
  n_graduate_experiments: 206,
  n_leaderboard_graduates: 40,
  n_surviving_deflation: 0,
  near_misses: [
    {
      symbol: 'CASY',
      strategy_name: 'rsi_mean_reversion',
      holdout_sharpe: 1.64,
      bar: 1.73,
      ratio_to_bar: 0.95,
      holdout_years: 4.3,
    },
  ],
  n_open_positions: 21,
  frontier: {
    n_symbols: 607,
    holdout_years: 4.3,
    power: 0.8,
    bar: 1.73,
    detectable_sharpe: 2.13,
    standard_error: 0.48,
  },
  book: {
    n_survivors: 0,
    n_non_survivors: 0,
    n_unknown: 21,
    survivor_mean_forward_sharpe: null,
    non_survivor_mean_forward_sharpe: null,
  },
}

describe('DeflationHeadline', () => {
  it('leads with how many graduates clear the selection-luck bar', () => {
    render(<DeflationHeadline report={report} />)
    expect(screen.getByTestId('deflation-survivors')).toHaveTextContent('0 of 40')
  })

  it('states the search effort behind those graduates', () => {
    render(<DeflationHeadline report={report} />)
    const effort = screen.getByTestId('search-effort')
    expect(effort).toHaveTextContent('3,208')
    expect(effort).toHaveTextContent('607')
    expect(effort).toHaveTextContent('115,009')
    expect(effort).toHaveTextContent(/sum of the per-symbol DSR\/MinTRL denominators/i)
  })

  it('lists the near-misses with each candidate’s own bar', () => {
    render(<DeflationHeadline report={report} />)
    const row = screen.getByRole('row', { name: /CASY/ })
    expect(row).toHaveTextContent('1.64')
    expect(row).toHaveTextContent('1.73')
  })

  it('says plainly when nothing clears the bar', () => {
    render(<DeflationHeadline report={report} />)
    expect(screen.getByRole('status')).toHaveTextContent(/not distinguishable from selection luck/i)
  })

  it('does not claim selection luck when something does clear the bar', () => {
    render(<DeflationHeadline report={{ ...report, n_surviving_deflation: 3 }} />)
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('states what an edge must BE, not just what it must show (ADR-043)', () => {
    render(<DeflationHeadline report={report} />)
    const resolution = screen.getByTestId('detection-frontier')
    expect(resolution).toHaveTextContent('2.13')
    expect(resolution).toHaveTextContent('80%')
    expect(resolution).toHaveTextContent('4.3')
  })

  it('omits the resolution line when no graduate fixes a holdout length', () => {
    render(<DeflationHeadline report={{ ...report, frontier: null }} />)
    expect(screen.queryByTestId('detection-frontier')).toBeNull()
  })

  it('omits the near-miss table when there are none', () => {
    render(<DeflationHeadline report={{ ...report, near_misses: [] }} />)
    expect(screen.queryByRole('table')).toBeNull()
  })
})

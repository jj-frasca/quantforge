// appShell store: holds the active page + a pending validation handoff. The handoff
// is the cross-page bridge that lets Compare Configs send the user to Validation
// with a config pre-loaded — that's the methodology arc this is here to close
// (parameter-sensitivity in Compare → out-of-sample penalty in Validation).
import { beforeEach, expect, test } from 'vitest'

import { useAppShell } from './appShell'

beforeEach(() => {
  // Reset the store between tests — Zustand stores are module-scoped singletons.
  useAppShell.setState({ activePage: 'data-explorer', pendingValidation: null })
})

test('starts on the Data Explorer page with no pending handoff', () => {
  expect(useAppShell.getState().activePage).toBe('data-explorer')
  expect(useAppShell.getState().pendingValidation).toBeNull()
})

test('setActivePage flips the current page', () => {
  useAppShell.getState().setActivePage('compare-configs')
  expect(useAppShell.getState().activePage).toBe('compare-configs')
})

test('requestValidation stores the handoff AND switches to the Validation page', () => {
  // This is the atomic guarantee that makes the cross-page bridge land in one
  // click: the page flip and the handoff must commit together. If they could
  // separate, the user could land on Validation with a stale form (handoff not
  // yet consumed) or stay on Compare with the handoff already set (no UI cue).
  useAppShell.getState().requestValidation({
    symbol: 'SPY',
    strategy: 'sma',
    startDate: '2020-01-01',
    endDate: '2024-01-01',
  })
  const state = useAppShell.getState()
  expect(state.activePage).toBe('validation')
  expect(state.pendingValidation).toEqual({
    symbol: 'SPY',
    strategy: 'sma',
    startDate: '2020-01-01',
    endDate: '2024-01-01',
  })
})

test('consumePendingValidation returns the handoff and clears it', () => {
  // Single-shot: ValidationReportPage reads on mount, then the store is empty.
  // This prevents a stale handoff from re-applying on re-navigation.
  useAppShell.setState({
    pendingValidation: {
      symbol: 'AAPL',
      strategy: 'rsi_mean_reversion',
      startDate: '2020-01-01',
      endDate: '2024-01-01',
    },
  })
  const handoff = useAppShell.getState().consumePendingValidation()
  expect(handoff?.symbol).toBe('AAPL')
  expect(useAppShell.getState().pendingValidation).toBeNull()
})

test('consumePendingValidation returns null when nothing is pending', () => {
  expect(useAppShell.getState().consumePendingValidation()).toBeNull()
})

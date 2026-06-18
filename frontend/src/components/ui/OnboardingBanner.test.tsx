// OnboardingBanner: a first-visit explainer above the primary nav. Renders the three-step
// flow ("Pick a strategy → Adjust if you want → See the result"), is dismissable, and
// persists the dismissal in localStorage so a returning user doesn't see it again.
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test } from 'vitest'

import { OnboardingBanner, ONBOARDING_DISMISSED_KEY } from './OnboardingBanner'

beforeEach(() => {
  // Each test starts with a clean slate — the banner under test owns this key entirely.
  window.localStorage.removeItem(ONBOARDING_DISMISSED_KEY)
})

test('renders the three-step explainer for a first-time visitor', () => {
  render(<OnboardingBanner />)
  const banner = screen.getByRole('region', { name: /getting started/i })
  expect(banner).toBeInTheDocument()
  expect(banner).toHaveTextContent(/pick a strategy/i)
  expect(banner).toHaveTextContent(/adjust/i)
  expect(banner).toHaveTextContent(/see the result/i)
})

test('renders nothing when the user has already dismissed it', () => {
  window.localStorage.setItem(ONBOARDING_DISMISSED_KEY, '1')
  render(<OnboardingBanner />)
  expect(screen.queryByRole('region', { name: /getting started/i })).not.toBeInTheDocument()
})

test('clicking dismiss hides the banner and writes to localStorage', async () => {
  render(<OnboardingBanner />)
  await userEvent.click(screen.getByRole('button', { name: /got it/i }))
  expect(screen.queryByRole('region', { name: /getting started/i })).not.toBeInTheDocument()
  expect(window.localStorage.getItem(ONBOARDING_DISMISSED_KEY)).toBe('1')
})

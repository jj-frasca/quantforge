// Term: renders the jargon child + an inline tooltip with the definition; the term
// itself is focusable (so the tooltip works on keyboard / touch, not just on hover);
// the browser-native `title` is set as the screen-reader fallback.
import { render, screen } from '@testing-library/react'

import { Term } from './Term'

test('renders the visible jargon and an inline definition tooltip', () => {
  render(
    <Term definition="Return per unit of risk; above 1 is good.">Sharpe</Term>,
  )
  expect(screen.getByText('Sharpe')).toBeInTheDocument()
  expect(
    screen.getByRole('tooltip', { name: /return per unit of risk/i }),
  ).toBeInTheDocument()
})

test('the term wrapper is focusable so the tooltip works on keyboard and touch', () => {
  // tabIndex={0} makes the element part of the tab order and grants :focus styling
  // for the CSS-driven tooltip. Without this the tooltip is hover-only — useless on
  // mobile and inaccessible on keyboard.
  render(<Term definition="…">PBO</Term>)
  const term = screen.getByText('PBO').closest('.term')
  expect(term).toHaveAttribute('tabindex', '0')
})

test('also sets the browser-native title attribute as the screen-reader fallback', () => {
  render(<Term definition="Year-over-year swings.">Vol</Term>)
  const term = screen.getByText('Vol').closest('.term')
  expect(term).toHaveAttribute('title', 'Year-over-year swings.')
})

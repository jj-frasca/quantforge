// Field: label is associated with the inner input; optional hint is visible (not just
// a hover tooltip).
import { render, screen } from '@testing-library/react'

import { Field } from './Field'

test('associates the label with the inner input via the wrapping <label>', () => {
  render(
    <Field label="Symbol">
      <input type="text" defaultValue="AAPL" />
    </Field>,
  )
  expect(screen.getByLabelText('Symbol')).toHaveValue('AAPL')
})

test('renders the hint text inline so the form is self-documenting (not hover-only)', () => {
  render(
    <Field label="Fast window" hint="Bars in the fast SMA">
      <input type="number" defaultValue={20} />
    </Field>,
  )
  // The hint should be visible in the rendered DOM, not just in a title= tooltip.
  expect(screen.getByText('Bars in the fast SMA')).toBeInTheDocument()
})

test('omits the hint element entirely when no hint is provided', () => {
  const { container } = render(
    <Field label="Symbol">
      <input type="text" />
    </Field>,
  )
  expect(container.querySelector('.field-hint')).toBeNull()
})

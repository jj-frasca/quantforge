// StrategyParamForm: one numeric <input> per ParamSchema. Williams %R's oversold/overbought
// params (backend catalog.py) are the only catalog params whose entire valid range is
// negative (default -80/-20, minimum -99/-49) -- every value a user could type there starts
// with "-".
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { expect, test } from 'vitest'

import type { ParamSchema } from '../../types/strategies'
import { StrategyParamForm } from './StrategyParamForm'

const oversold: ParamSchema = {
  name: 'oversold',
  type: 'float',
  default: -80,
  minimum: -99,
  maximum: -51,
  step: 1,
  label: 'Oversold threshold',
  description: null,
}

function Harness() {
  const [values, setValues] = useState<Record<string, number>>({ oversold: -80 })
  return (
    <>
      <StrategyParamForm parameters={[oversold]} values={values} onChange={setValues} />
      <output data-testid="stored">{values.oversold}</output>
    </>
  )
}

test('typing a negative value keeps the minus sign instead of being silently dropped', async () => {
  const user = userEvent.setup()
  render(<Harness />)

  const input = screen.getByLabelText(/oversold threshold/i)
  await user.clear(input)
  await user.type(input, '-85')

  expect(input).toHaveValue(-85)
  expect(screen.getByTestId('stored')).toHaveTextContent('-85')
})

const uncappedRatio: ParamSchema = {
  name: 'z_scale',
  type: 'float',
  default: 1.5,
  minimum: null,
  maximum: null,
  step: null,
  label: 'Z scale',
  description: null,
}

function UncappedHarness() {
  const [values, setValues] = useState<Record<string, number>>({ z_scale: 1.5 })
  return <StrategyParamForm parameters={[uncappedRatio]} values={values} onChange={setValues} />
}

test('a param with no minimum/step (both nullable in the schema) renders without a min bound and with a free-form step', () => {
  // Every current catalog entry happens to set minimum + step, so this schema-legal
  // combination (ParamSchema.minimum/step are `z.number().nullable().optional()`) had
  // never been exercised — `param.minimum ?? undefined` and the float fallback to
  // `step="any"` both sat uncovered.
  render(<UncappedHarness />)
  const input = screen.getByLabelText(/z scale/i)
  expect(input).not.toHaveAttribute('min')
  expect(input).toHaveAttribute('step', 'any')
})

// A second, more direct regression -- asserting the DOM value literally stays "-" after
// one keystroke -- is NOT expressible here: jsdom's input[type=number] returns "" from
// `.value` for an in-progress invalid number in BOTH the buggy and fixed implementation
// (confirmed against a real Chromium build too: the *script-readable* `.value` is "" the
// instant the character is typed either way). What differs, and what actually matters to a
// user, is only visible in real layout -- a real browser keeps rendering the "-" the user
// just typed (an internal "user interface value" distinct from the IDL `.value`) *unless*
// something reassigns `.value` via script, which is exactly what a controlled `value={...}`
// prop does on every keystroke's re-render. That reassignment was verified live with
// Playwright against Chrome for Testing this session: typing "-" showed "-" on screen while
// `.value` read ""; then running `el.value = ''` (what the old controlled render did every
// keystroke) visibly wiped the "-" from the screen. The fix makes the input intentionally
// uncontrolled (`defaultValue` + a ref-driven effect gated on `document.activeElement !==
// el`) so that reassignment never happens while the field is focused -- see
// StrategyParamForm.tsx's comment for the mechanism. No jsdom-expressible assertion for
// that mechanism was found; this is recorded here rather than silently shipping without one.

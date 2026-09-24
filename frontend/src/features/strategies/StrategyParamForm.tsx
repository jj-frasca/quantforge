import { useEffect, useRef } from 'react'

import { Field } from '../../components/ui/Field'
import type { ParamSchema } from '../../types/strategies'

interface Props {
  parameters: ParamSchema[]
  values: Record<string, number>
  onChange: (next: Record<string, number>) => void
}

// Renders one labelled numeric input per ParamSchema. The control type (int/float) and
// the min/max/step constraints come from the backend catalog — adding a strategy with
// new parameters lights up form fields here automatically.
export function StrategyParamForm({ parameters, values, onChange }: Props) {
  return (
    <>
      {parameters.map((param) => (
        <ParamInput
          key={param.name}
          param={param}
          value={values[param.name]}
          onChange={(next) => onChange({ ...values, [param.name]: next })}
        />
      ))}
    </>
  )
}

function ParamInput({
  param,
  value,
  onChange,
}: {
  param: ParamSchema
  value: number
  onChange: (next: number) => void
}) {
  // Deliberately uncontrolled (`defaultValue`, not `value`): an `input[type=number]`
  // sanitizes any script-assigned value that isn't a complete parseable number down to
  // "" (spec'd browser behaviour, not a jsdom quirk) — a controlled `value` re-syncs on
  // every keystroke's re-render, so a bare "-" while typing a negative number (Williams
  // %R's oversold/overbought range is entirely negative) got wiped before the digits
  // that would have made it valid could follow. Left uncontrolled, the browser's own
  // in-progress typing state is never touched; the effect below only pushes an
  // externally-driven value (preset click, strategy switch) into the DOM, and only
  // while this field isn't the one being typed into.
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const el = inputRef.current
    if (el && document.activeElement !== el) {
      el.value = Number.isFinite(value) ? String(value) : ''
    }
  }, [value])

  return (
    <Field label={param.label} hint={param.description ?? undefined}>
      <input
        ref={inputRef}
        type="number"
        min={param.minimum ?? undefined}
        max={param.maximum ?? undefined}
        step={param.step ?? (param.type === 'int' ? 1 : 'any')}
        defaultValue={Number.isFinite(value) ? value : ''}
        title={param.description ?? undefined}
        onChange={(event) => {
          const raw = event.target.value
          if (raw === '') {
            // Allow the input to be temporarily empty during edit (e.g., after
            // clear()). Store NaN so submit-time validation catches missing values.
            onChange(Number.NaN)
            return
          }
          const parsed = param.type === 'int' ? parseInt(raw, 10) : parseFloat(raw)
          onChange(parsed)
        }}
      />
    </Field>
  )
}

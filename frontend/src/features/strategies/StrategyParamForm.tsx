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
      {parameters.map((param) => {
        const stored = values[param.name]
        const display = Number.isFinite(stored) ? stored : ''
        return (
          <Field key={param.name} label={param.label}>
            <input
              type="number"
              min={param.minimum ?? undefined}
              max={param.maximum ?? undefined}
              step={param.step ?? (param.type === 'int' ? 1 : 'any')}
              value={display}
              title={param.description ?? undefined}
              onChange={(event) => {
                const raw = event.target.value
                if (raw === '') {
                  // Allow the input to be temporarily empty during edit (e.g., after
                  // clear()). Store NaN so the render shows ''; submit-time validation
                  // catches missing values.
                  onChange({ ...values, [param.name]: Number.NaN })
                  return
                }
                const parsed = param.type === 'int' ? parseInt(raw, 10) : parseFloat(raw)
                onChange({ ...values, [param.name]: parsed })
              }}
            />
          </Field>
        )
      })}
    </>
  )
}

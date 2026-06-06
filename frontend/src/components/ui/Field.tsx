import type { ReactNode } from 'react'

interface Props {
  label: string
  /**
   * Optional sub-label rendered below the input. Used to surface the backend catalog's
   * per-parameter `description` so the form is self-documenting instead of relying on
   * hover tooltips.
   */
  hint?: string
  children: ReactNode
}

// Labelled-input wrapper used across the form-driven pages. Keeps the markup uniform
// (label on top, input below, optional hint below the input) so styling stays in
// one place.
export function Field({ label, hint, children }: Props) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

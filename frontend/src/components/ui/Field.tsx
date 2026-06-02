import type { ReactNode } from 'react'

interface Props {
  label: string
  children: ReactNode
}

// Labelled-input wrapper used across the form-driven pages. Keeps the markup uniform
// (label on top, input below) so styling can stay in one place.
export function Field({ label, children }: Props) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  )
}

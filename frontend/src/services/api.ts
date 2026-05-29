import {
  validationReportSchema,
  type ValidateRequest,
  type ValidationReport,
} from '../types/validation'

// Same-origin by default; dev/prod can proxy /api to the backend.
const API_BASE = ''

export async function requestValidation(body: ValidateRequest): Promise<ValidationReport> {
  const response = await fetch(`${API_BASE}/api/v1/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`Validation request failed (${response.status})`)
  }
  // Validate the response shape at the boundary — never trust the network.
  return validationReportSchema.parse(await response.json())
}

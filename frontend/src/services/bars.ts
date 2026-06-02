import { barsResponseSchema, type BarsQuery, type BarsResponse } from '../types/bars'

const API_BASE = ''

export async function requestBars(query: BarsQuery): Promise<BarsResponse> {
  const params = new URLSearchParams({ ...query })
  const response = await fetch(`${API_BASE}/api/v1/bars?${params.toString()}`)
  if (!response.ok) {
    const detail = await response.json().then(
      (parsed: unknown) => {
        if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
          const value = (parsed as { detail?: unknown }).detail
          return typeof value === 'string' ? `: ${value}` : ''
        }
        return ''
      },
      () => '',
    )
    throw new Error(`Bars request failed (${response.status})${detail}`)
  }
  return barsResponseSchema.parse(await response.json())
}

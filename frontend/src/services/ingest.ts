import {
  ingestResponseSchema,
  type IngestRequest,
  type IngestResponse,
} from '../types/ingest'

const API_BASE = ''

export async function requestIngest(body: IngestRequest): Promise<IngestResponse> {
  const response = await fetch(`${API_BASE}/api/v1/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    // Surface the backend's `detail` (e.g. "insufficient data") when present.
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
    throw new Error(`Ingest request failed (${response.status})${detail}`)
  }
  return ingestResponseSchema.parse(await response.json())
}

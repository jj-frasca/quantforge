import {
  backtestResponseSchema,
  type BacktestRequest,
  type BacktestResponse,
} from '../types/backtest'

const API_BASE = ''

export async function requestBacktest(body: BacktestRequest): Promise<BacktestResponse> {
  const response = await fetch(`${API_BASE}/api/v1/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
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
    throw new Error(`Backtest request failed (${response.status})${detail}`)
  }
  return backtestResponseSchema.parse(await response.json())
}

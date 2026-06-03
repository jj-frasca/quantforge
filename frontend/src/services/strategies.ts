import { strategyCatalogSchema, type StrategyCatalog } from '../types/strategies'

const API_BASE = ''

export async function requestStrategies(): Promise<StrategyCatalog> {
  const response = await fetch(`${API_BASE}/api/v1/strategies`)
  if (!response.ok) {
    throw new Error(`Strategies request failed (${response.status})`)
  }
  return strategyCatalogSchema.parse(await response.json())
}

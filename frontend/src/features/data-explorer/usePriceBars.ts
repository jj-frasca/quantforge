import { useQuery } from '@tanstack/react-query'

import { requestBars } from '../../services/bars'
import type { BarsQuery } from '../../types/bars'

// Read-only fetch -> useQuery. `enabled` is false until the user submits the form,
// so the chart doesn't fire a request on initial render.
export function usePriceBars(query: BarsQuery | null) {
  return useQuery({
    queryKey: ['bars', query],
    queryFn: () => {
      if (!query) throw new Error('usePriceBars called without a query')
      return requestBars(query)
    },
    enabled: query !== null,
    staleTime: 60_000,
  })
}

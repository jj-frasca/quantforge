import { useQuery } from '@tanstack/react-query'

import { requestWindowComparison } from '../../services/lab'

// Recomputed from the pool on every request, so it moves as the daily discovery re-searches
// symbols at the current window — the paired sample only ever grows.
export function useWindowComparison() {
  return useQuery({
    queryKey: ['window-comparison'],
    queryFn: requestWindowComparison,
  })
}

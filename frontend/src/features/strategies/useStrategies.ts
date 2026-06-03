import { useQuery } from '@tanstack/react-query'

import { requestStrategies } from '../../services/strategies'

// The catalog rarely changes during a session, so cache it once and re-use it across
// the Backtest Results and Validation Report pages. staleTime: Infinity means we won't
// refetch on focus/mount — the user will get a fresh catalog on a hard reload.
export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: requestStrategies,
    staleTime: Infinity,
  })
}

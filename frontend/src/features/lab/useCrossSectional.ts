import { useQuery } from '@tanstack/react-query'

import { requestCrossSectional } from '../../services/lab'

// The latest cross-sectional hunt (data/cross_sectional_pool.json, ADR-024) — advances weekly via
// the scheduled cloud hunt. Null until a hunt has produced a record.
export function useCrossSectional() {
  return useQuery({
    queryKey: ['cross-sectional'],
    queryFn: requestCrossSectional,
  })
}

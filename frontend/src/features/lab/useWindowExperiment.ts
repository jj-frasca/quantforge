import { useQuery } from '@tanstack/react-query'

import { requestWindowExperiment } from '../../services/lab'

// ADR-076/077: parsed from a committed artifact, so unlike useWindowComparison this does NOT move
// as the pool grows. It is a spent two-look sequence; re-deriving it would be a third look.
export function useWindowExperiment() {
  return useQuery({
    queryKey: ['window-experiment'],
    queryFn: requestWindowExperiment,
  })
}

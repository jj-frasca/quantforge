import { useQuery } from '@tanstack/react-query'

import { requestNullComparison } from '../../services/lab'

// Recomputed from the pool and the null artifacts on every request, so it moves whenever the daily
// discovery writes an experiment — unlike the calibration itself, which only moves on a re-run.
export function useNullComparison() {
  return useQuery({
    queryKey: ['null-comparison'],
    queryFn: requestNullComparison,
  })
}

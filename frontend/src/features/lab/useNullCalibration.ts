import { useQuery } from '@tanstack/react-query'

import { requestNullCalibration } from '../../services/lab'

// The calibration changes only when the null-calibration workflow runs (monthly, or on demand after
// a GateConfig change), so it is the least volatile thing on the dashboard.
export function useNullCalibration() {
  return useQuery({
    queryKey: ['null-calibration'],
    queryFn: requestNullCalibration,
  })
}

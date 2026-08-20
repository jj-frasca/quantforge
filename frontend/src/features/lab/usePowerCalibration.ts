import { useQuery } from '@tanstack/react-query'

import { requestPowerCalibration } from '../../services/lab'

// Like the null calibration, this changes only when a power workflow runs, so it is among the
// least volatile things on the dashboard.
export function usePowerCalibration() {
  return useQuery({
    queryKey: ['power-calibration'],
    queryFn: requestPowerCalibration,
  })
}

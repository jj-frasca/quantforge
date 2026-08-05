import { useQuery } from '@tanstack/react-query'

import { requestEquityCurve } from '../../services/lab'

// The equity curve is the committed paper-account snapshot series (data/equity_curve.json) — it grows
// only when the broker run appends a point, so a short stale window is plenty.
export function useEquityCurve() {
  return useQuery({
    queryKey: ['equity-curve'],
    queryFn: requestEquityCurve,
  })
}

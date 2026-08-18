import { useQuery } from '@tanstack/react-query'

import { requestPoolReport } from '../../services/lab'

// The pool report summarizes the committed research pool (data/research_pool/) and paper book, so
// it changes only when a scheduled hunt runs — the same cadence as the leaderboard.
export function usePoolReport() {
  return useQuery({
    queryKey: ['pool-report'],
    queryFn: requestPoolReport,
  })
}

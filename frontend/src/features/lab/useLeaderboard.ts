import { useQuery } from '@tanstack/react-query'

import { requestLeaderboard } from '../../services/lab'

// The leaderboard is the committed research pool (data/research_pool.json) — it changes only when
// a hunt runs, so a short stale window is plenty; the user gets fresh data on remount/reload.
export function useLeaderboard() {
  return useQuery({
    queryKey: ['leaderboard'],
    queryFn: requestLeaderboard,
  })
}

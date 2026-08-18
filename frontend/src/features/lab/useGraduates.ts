import { useQuery } from '@tanstack/react-query'

import { requestGraduates } from '../../services/lab'

// The graduates are the committed research pool's cleared-the-gate experiments
// (data/research_pool/) — they change only when a hunt runs, so a short stale window is plenty.
export function useGraduates() {
  return useQuery({
    queryKey: ['graduates'],
    queryFn: requestGraduates,
  })
}

import { useQuery } from '@tanstack/react-query'

import { requestPaperPortfolio } from '../../services/lab'

// The paper book (data/paper_portfolio.json) advances daily via the cloud forward-accrual loop.
export function usePaperPortfolio() {
  return useQuery({
    queryKey: ['paper-portfolio'],
    queryFn: requestPaperPortfolio,
  })
}

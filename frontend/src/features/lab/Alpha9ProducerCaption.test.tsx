import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'

import { server } from '../../test/server'
import { renderWithClient } from '../../test/utils'
import { CrossSectionalPanel } from './CrossSectionalPanel'

test('qualifies production Alpha9 and trailing-high support alongside audited direct-shift recipes', async () => {
  server.use(http.get('/api/v1/cross-sectional', () => HttpResponse.json({
    created_at: '2026-10-23T10:00:00Z', universe_size: 20, graduated: false, trials: [],
  })))
  renderWithClient(<CrossSectionalPanel />)
  const caption = await screen.findByText(/Purged CV support is restricted to audited family recipes/i)
  expect(caption).toHaveTextContent(/audited direct-shift recipes/i)
  expect(caption).toHaveTextContent(/trailing-high and Alpha9 price-change-extrema recipes restricted to pandas 3\.0\.6 Cython on complete native Float64 panels/i)
  for (const caveat of [/later training is intentional/i,
    /winning family uses the complete search sample/i,
    /account entry and switching trades are not reconciled/i,
    /benchmark adds no turnover-cost model/i,
    /static snapshots, not historical point-in-time/i,
    /equal means of retained-fold Sharpes/i,
    /not Sharpe on stitched policy returns/i]) {
    expect(caption).toHaveTextContent(caveat)
  }
})

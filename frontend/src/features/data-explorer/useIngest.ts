import { useMutation } from '@tanstack/react-query'

import { requestIngest } from '../../services/ingest'
import type { IngestRequest } from '../../types/ingest'

// Ingestion is a side-effecting POST run on demand -> a mutation, not a cached query.
export function useIngest() {
  return useMutation({
    mutationFn: (body: IngestRequest) => requestIngest(body),
  })
}

import { useMutation } from '@tanstack/react-query'

import { requestValidation } from '../../services/api'
import type { ValidateRequest } from '../../types/validation'

// Validation is run on demand against a config grid -> a mutation, not a cached query.
export function useValidation() {
  return useMutation({
    mutationFn: (body: ValidateRequest) => requestValidation(body),
  })
}

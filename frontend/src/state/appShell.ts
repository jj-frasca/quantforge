import { create } from 'zustand'

// The cross-page bridge from Compare Configs to Validation: pre-fills the Validation
// form with the (symbol, strategy, window) the user picked for a specific Compare
// row, so they can answer "does this look-good config survive PBO?" in one click.
// Param values are intentionally not part of the handoff — /validate auto-generates
// its grid from the catalog (ADR-010 §Consequences).
export interface ValidationHandoff {
  symbol: string
  strategy: string
  startDate: string
  endDate: string
}

export type PageId =
  | 'data-explorer'
  | 'backtest-results'
  | 'compare-configs'
  | 'validation'
  | 'lab'
  | 'about'

interface AppShellState {
  activePage: PageId
  pendingValidation: ValidationHandoff | null
  setActivePage: (page: PageId) => void
  // requestValidation must commit BOTH state changes atomically so a user click
  // never lands them on Validation without a pending handoff (or vice versa).
  requestValidation: (handoff: ValidationHandoff) => void
  consumePendingValidation: () => ValidationHandoff | null
}

export const useAppShell = create<AppShellState>((set, get) => ({
  activePage: 'data-explorer',
  pendingValidation: null,
  setActivePage: (page) => set({ activePage: page }),
  requestValidation: (handoff) =>
    set({ pendingValidation: handoff, activePage: 'validation' }),
  consumePendingValidation: () => {
    const current = get().pendingValidation
    if (current === null) return null
    set({ pendingValidation: null })
    return current
  },
}))

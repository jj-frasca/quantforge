import {
  crossSectionalResponseSchema,
  graduatesSchema,
  leaderboardSchema,
  paperPortfolioSchema,
  type CrossSectionalView,
  type GraduateRow,
  type LeaderboardRow,
  type PaperPosition,
} from '../types/lab'

const API_BASE = ''

export async function requestLeaderboard(): Promise<LeaderboardRow[]> {
  const response = await fetch(`${API_BASE}/api/v1/leaderboard`)
  if (!response.ok) {
    throw new Error(`Leaderboard request failed (${response.status})`)
  }
  return leaderboardSchema.parse(await response.json())
}

export async function requestGraduates(): Promise<GraduateRow[]> {
  const response = await fetch(`${API_BASE}/api/v1/graduates`)
  if (!response.ok) {
    throw new Error(`Graduates request failed (${response.status})`)
  }
  return graduatesSchema.parse(await response.json())
}

export async function requestCrossSectional(): Promise<CrossSectionalView | null> {
  const response = await fetch(`${API_BASE}/api/v1/cross-sectional`)
  if (!response.ok) {
    throw new Error(`Cross-sectional request failed (${response.status})`)
  }
  return crossSectionalResponseSchema.parse(await response.json())
}

export async function requestPaperPortfolio(): Promise<PaperPosition[]> {
  const response = await fetch(`${API_BASE}/api/v1/paper-portfolio`)
  if (!response.ok) {
    throw new Error(`Paper portfolio request failed (${response.status})`)
  }
  return paperPortfolioSchema.parse(await response.json())
}

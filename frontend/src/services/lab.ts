import { z } from 'zod'

import {
  crossSectionalResponseSchema,
  equityCurveSchema,
  graduatesSchema,
  leaderboardSchema,
  nullCalibrationSchema,
  nullComparisonSchema,
  powerSweepSchema,
  paperPortfolioSchema,
  poolReportSchema,
  type CrossSectionalView,
  type EquityPoint,
  type GraduateRow,
  type LeaderboardRow,
  type NullCalibration,
  type NullComparison,
  type PaperPosition,
  type PoolReport,
  type PowerSweep,
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

export async function requestEquityCurve(): Promise<EquityPoint[]> {
  const response = await fetch(`${API_BASE}/api/v1/equity-curve`)
  if (!response.ok) {
    throw new Error(`Equity curve request failed (${response.status})`)
  }
  return equityCurveSchema.parse(await response.json())
}

export async function requestPaperPortfolio(): Promise<PaperPosition[]> {
  const response = await fetch(`${API_BASE}/api/v1/paper-portfolio`)
  if (!response.ok) {
    throw new Error(`Paper portfolio request failed (${response.status})`)
  }
  return paperPortfolioSchema.parse(await response.json())
}

export async function requestPoolReport(): Promise<PoolReport> {
  const response = await fetch(`${API_BASE}/api/v1/pool-report`)
  if (!response.ok) {
    throw new Error(`Pool report request failed (${response.status})`)
  }
  return poolReportSchema.parse(await response.json())
}

export async function requestNullCalibration(): Promise<NullCalibration[]> {
  const response = await fetch(`${API_BASE}/api/v1/null-calibration`)
  if (!response.ok) {
    throw new Error(`Null calibration request failed (${response.status})`)
  }
  return z.array(nullCalibrationSchema).parse(await response.json())
}

export async function requestNullComparison(): Promise<NullComparison[]> {
  const response = await fetch(`${API_BASE}/api/v1/null-comparison`)
  if (!response.ok) {
    throw new Error(`Null comparison request failed (${response.status})`)
  }
  return z.array(nullComparisonSchema).parse(await response.json())
}

export async function requestPowerCalibration(): Promise<PowerSweep[]> {
  const response = await fetch(`${API_BASE}/api/v1/power-calibration`)
  if (!response.ok) {
    throw new Error(`Power calibration request failed (${response.status})`)
  }
  return z.array(powerSweepSchema).parse(await response.json())
}

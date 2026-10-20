import {
  crossSectionalResponseSchema,
  graduatesSchema,
  leaderboardSchema,
  paperPortfolioSchema,
  nullCalibrationSchema,
  powerSweepSchema,
  type LeaderboardRow,
  type PaperPosition,
} from './lab'

test('nullCalibrationSchema preserves the measured history identity', () => {
  const parsed = nullCalibrationSchema.parse({
    n_symbols: 1,
    n_graduates: 0,
    false_graduation_rate: 0,
    n_clear_deflation_bar: 0,
    deflation_bar: 1,
    max_deflated_sharpe: -0.1,
    max_holdout_sharpe: null,
    gate_config_version: 'gate',
    search_config_version: 'search',
    null_mode: 'iid_normal',
    n_bars: [5400],
  })

  expect(parsed.n_bars).toEqual([5400])
})

test('graduatesSchema parses a graduate row incl. undervaluation + deflation verdict', () => {
  const raw = [
    {
      symbol: 'CRM',
      strategy_name: 'trend_filtered_mean_reversion',
      deflated_sharpe: 0.44,
      holdout_sharpe: 0.5,
      survives_universe_deflation: false,
      undervaluation_score: 0.7,
    },
  ]
  const parsed = graduatesSchema.parse(raw)
  expect(parsed[0].survives_universe_deflation).toBe(false)
  expect(parsed[0].undervaluation_score).toBe(0.7)
})

test('graduatesSchema tolerates null undervaluation / deflation (unscorable name)', () => {
  const parsed = graduatesSchema.parse([
    {
      symbol: 'SPY',
      strategy_name: 'sma',
      deflated_sharpe: 0.3,
      holdout_sharpe: 0.2,
      survives_universe_deflation: null,
      undervaluation_score: null,
    },
  ])
  expect(parsed[0].undervaluation_score).toBeNull()
})

test('crossSectionalResponseSchema parses a hunt view with trials', () => {
  const parsed = crossSectionalResponseSchema.parse({
    created_at: '2026-07-26T10:00:00Z',
    universe_size: 51,
    best_strategy_name: 'xs_momentum',
    graduated: false,
    graduate_holdout_sharpe: null,
    trials: [
      {
        strategy_name: 'xs_momentum',
        observed_sharpe: 0.5,
        deflated_sharpe: -0.08,
        pbo: 0.44,
        parameter_stability_score: 0.22,
        ic_mean: 0.021,
        ic_t_stat: 3.42,
      },
    ],
  })
  expect(parsed?.universe_size).toBe(51)
  expect(parsed?.trials[0].pbo).toBe(0.44)
  expect(parsed?.trials[0].ic_mean).toBe(0.021)
})

test('crossSectionalResponseSchema accepts a trial recorded before ADR-035 (no IC)', () => {
  const parsed = crossSectionalResponseSchema.parse({
    created_at: '2026-07-26T10:00:00Z',
    universe_size: 51,
    best_strategy_name: 'xs_momentum',
    graduated: false,
    graduate_holdout_sharpe: null,
    trials: [
      {
        strategy_name: 'xs_momentum',
        observed_sharpe: 0.5,
        deflated_sharpe: -0.08,
        pbo: 0.44,
        parameter_stability_score: 0.22,
      },
    ],
  })
  expect(parsed?.trials[0].ic_mean).toBeUndefined()
})

test('crossSectionalResponseSchema parses null (no hunt yet)', () => {
  expect(crossSectionalResponseSchema.parse(null)).toBeNull()
})

test('leaderboardSchema parses a graduate row with holdout + deflation fields', () => {
  const raw = [
    {
      symbol: 'CRM',
      strategy_name: 'trend_filtered_mean_reversion',
      deflated_sharpe: 0.28,
      graduated: true,
      holdout_sharpe: 0.44,
      survives_universe_deflation: false,
    },
  ]
  const parsed = leaderboardSchema.parse(raw)
  expect(parsed[0].symbol).toBe('CRM')
  expect(parsed[0].graduated).toBe(true)
  expect(parsed[0].holdout_sharpe).toBe(0.44)
})

test('leaderboardSchema tolerates a non-graduate row with null holdout fields', () => {
  const raw = [
    {
      symbol: 'SPY',
      strategy_name: 'donchian_breakout',
      deflated_sharpe: -0.12,
      graduated: false,
      holdout_sharpe: null,
      survives_universe_deflation: null,
    },
  ]
  const parsed = leaderboardSchema.parse(raw)
  expect(parsed[0].graduated).toBe(false)
  expect(parsed[0].holdout_sharpe).toBeNull()
})

test('paperPortfolioSchema parses an open position with a forward score + equity series', () => {
  const raw = [
    {
      symbol: 'CRM',
      strategy_name: 'trend_filtered_mean_reversion',
      parameters: { window: 20, k: 2.0 },
      frozen_at: '2026-07-06T00:00:00Z',
      score: {
        forward_bars: 2,
        forward_return: 0.08,
        forward_sharpe: 0.9,
        buy_and_hold_return: -0.146,
        buy_and_hold_sharpe: -0.4,
        beats_buy_and_hold: true,
        forward_trades: 7,
        as_of: '2026-07-08T00:00:00Z',
        forward_equity: [
          { timestamp: '2026-07-07T00:00:00Z', strategy_equity: 1.02, buy_and_hold_equity: 0.99 },
          { timestamp: '2026-07-08T00:00:00Z', strategy_equity: 1.08, buy_and_hold_equity: 0.854 },
        ],
      },
      status: 'open',
      closed_at: null,
      exit_reasons: [],
    },
  ]
  const parsed = paperPortfolioSchema.parse(raw)
  expect(parsed[0].status).toBe('open')
  expect(parsed[0].score?.beats_buy_and_hold).toBe(true)
  expect(parsed[0].score?.forward_equity).toHaveLength(2)
  expect(parsed[0].score?.forward_equity[0].strategy_equity).toBe(1.02)
})

test('forwardScoreSchema defaults forward_equity to [] when absent (pre-ADR-023 scores)', () => {
  const raw = [
    {
      symbol: 'AAPL',
      strategy_name: 'sma',
      parameters: {},
      frozen_at: '2026-07-06T00:00:00Z',
      score: {
        forward_bars: 0,
        forward_return: 0.0,
        forward_sharpe: 0.0,
        buy_and_hold_return: 0.0,
        buy_and_hold_sharpe: 0.0,
        beats_buy_and_hold: false,
        forward_trades: 7,
        as_of: '2026-07-08T00:00:00Z',
      },
      status: 'open',
      exit_reasons: [],
    },
  ]
  const parsed = paperPortfolioSchema.parse(raw)
  expect(parsed[0].score?.forward_equity).toEqual([])
})

test('paperPortfolioSchema parses a closed position with exit reasons and null score', () => {
  const raw = [
    {
      symbol: 'LOW',
      strategy_name: 'rsi_mean_reversion',
      parameters: { period: 14 },
      frozen_at: '2026-07-06T00:00:00Z',
      score: null,
      status: 'closed',
      closed_at: '2026-08-01T00:00:00Z',
      exit_reasons: ['rolling Sharpe -0.10 <= 0.0 (edge has decayed)'],
    },
  ]
  const parsed = paperPortfolioSchema.parse(raw)
  expect(parsed[0].status).toBe('closed')
  expect(parsed[0].score).toBeNull()
  expect(parsed[0].exit_reasons).toHaveLength(1)
})

test('paperPortfolioSchema rejects an unknown status (boundary guard)', () => {
  const raw = [
    {
      symbol: 'AAPL',
      strategy_name: 'sma',
      parameters: {},
      frozen_at: '2026-07-06T00:00:00Z',
      status: 'paused',
      exit_reasons: [],
    },
  ]
  expect(() => paperPortfolioSchema.parse(raw)).toThrow()
})

// Type-level smoke: the inferred types are exported for components to consume.
test('exported types are usable', () => {
  const row: LeaderboardRow = {
    symbol: 'X',
    strategy_name: 'sma',
    deflated_sharpe: 0,
    graduated: false,
  }
  const pos: PaperPosition = {
    symbol: 'X',
    strategy_name: 'sma',
    parameters: {},
    frozen_at: '2026-07-06T00:00:00Z',
    status: 'open',
    exit_reasons: [],
  }
  expect(row.symbol).toBe(pos.symbol)
})

const compatibility = {
  status: 'DIFFERENT', search: 'DIFFERENT', gate: 'MATCHED', history: 'UNKNOWN',
  reasons: ['Recorded search differs.'],
  reference: {
    search_config_version: 'current-search', gate_config_version: 'current-gate',
    n_bars: 7400, strategy_names: ['manual'], n_per_param: 3,
    refine: true, refine_span: 0.25, select_by: 'observed',
  },
}
const manualNull = {
  n_symbols: 1, n_graduates: 0, false_graduation_rate: 0,
  n_clear_deflation_bar: 0, deflation_bar: 2, max_deflated_sharpe: -0.1,
  max_holdout_sharpe: null, gate_config_version: 'recorded-gate', null_mode: 'manual',
}
const manualPower = {
  edge: 'ar1', gate_config_version: 'recorded-gate', search_config_version: 'recorded-search',
  n_bars: 5400, cells: [],
}
for (const [name, schema, measured] of [
  ['null', nullCalibrationSchema, manualNull], ['power', powerSweepSchema, manualPower],
] as const) {
  test.each(['MATCHED', 'DIFFERENT', 'UNKNOWN'])(`${name} preserves %s compatibility`, (status) => {
    const context = { ...compatibility, status }
    expect(schema.parse({ ...measured, compatibility: context })).toMatchObject({ compatibility: context })
  })
  test(`${name} accepts older and unavailable metadata but rejects malformed metadata`, () => {
    expect(schema.safeParse(measured).success).toBe(true)
    expect(schema.safeParse({ ...measured, compatibility: null }).success).toBe(true)
    expect(schema.safeParse({ ...measured, compatibility: { ...compatibility, reference: null } }).success).toBe(true)
    expect(schema.safeParse({ ...measured, compatibility: { ...compatibility, reference: { ...compatibility.reference, select_by: 'walk_forward', refine: false } } }).success).toBe(true)
    expect(schema.safeParse({ ...measured, compatibility: { ...compatibility, gate: 'CURRENT' } }).success).toBe(false)
    expect(schema.safeParse({ ...measured, compatibility: { ...compatibility, reasons: 'missing identity' } }).success).toBe(false)
    expect(schema.safeParse({ ...measured, compatibility: { ...compatibility, status: 'CURRENT' } }).success).toBe(false)
    expect(schema.safeParse({ ...measured, compatibility: { ...compatibility, reference: {} } }).success).toBe(false)
    expect(schema.safeParse({ ...measured, compatibility: { ...compatibility, reference: { ...compatibility.reference, n_bars: 0 } } }).success).toBe(false)
  })
}

const referenceCell = {
  n_symbols: 2, n_detected: 1, detection_rate: 0.5, n_clear_deflation_bar: 1,
  deflation_bar: 2, edge: 'ar1', phi: 0.3, gate_config_version: 'v1',
}
test.each([
  { method: 'ar1_phi_lag_sign_v1', drift: null },
  ...[0, -0.0004, 1e-12].map((drift) => ({ method: 'ar1_conditional_mean_sign_v1', drift })), null,
])('retains explicit sweep and cell reference %j', (ar1_reference) => {
  expect(powerSweepSchema.parse({ ...manualPower, ar1_reference,
    cells: [{ ...referenceCell, ar1_reference }] })).toMatchObject({ ar1_reference, cells: [{ ar1_reference }] })
})
test.each([
  {}, { method: 'future', drift: 0 }, { method: 'ar1_phi_lag_sign_v1', drift: 0 },
  { method: 'ar1_conditional_mean_sign_v1', drift: null },
  { method: 'ar1_conditional_mean_sign_v1', drift: '0' },
  { method: 'ar1_conditional_mean_sign_v1', drift: true },
  { method: 'ar1_conditional_mean_sign_v1', drift: Infinity },
  { method: 'ar1_conditional_mean_sign_v1', drift: 0, extra: true },
])('rejects malformed reference at either boundary: %j', (ar1_reference) => {
  expect(powerSweepSchema.safeParse({ ...manualPower, ar1_reference }).success).toBe(false)
  expect(powerSweepSchema.safeParse({ ...manualPower, cells: [{ ...referenceCell, ar1_reference }] }).success).toBe(false)
})
test('preserves historical absence without scientific shadow validation', () => {
  expect(powerSweepSchema.parse(manualPower)).not.toHaveProperty('ar1_reference')
  expect(powerSweepSchema.parse({ ...manualPower, cells: [{ ...referenceCell, phi: 3,
    ar1_reference: { method: 'ar1_conditional_mean_sign_v1', drift: 0 } }] }).cells[0]).toMatchObject({ phi: 3, ar1_reference: { drift: 0 } })
})

const bandReference = {
  method: 'band_conditional_simple_mean_sign_zero_start_v1', drift: 0,
  total_vol: 0.01, start_price: 100,
}
test.each([0, -0.0004, 1e-12])('retains explicit band law and per-cell share with drift %s', (drift) => {
  const band_reference = { ...bandReference, drift }
  expect(powerSweepSchema.parse({ ...manualPower, band_reference,
    cells: [{ ...referenceCell, edge: 'band_reversion', phi: null, half_life: 5,
      deviation_share: 1, band_reference }] })).toMatchObject({ band_reference,
    cells: [{ half_life: 5, deviation_share: 1, band_reference }] })
})
test.each([
  {}, { ...bandReference, method: 'future' }, { ...bandReference, extra: true },
  ...['drift', 'total_vol', 'start_price'].flatMap((field) =>
    [undefined, null, '0', true, NaN, Infinity, -Infinity].map((value) => ({ ...bandReference, [field]: value }))),
])('refuses malformed band reference at both boundaries: %j', (band_reference) => {
  expect(powerSweepSchema.safeParse({ ...manualPower, band_reference }).success).toBe(false)
  expect(powerSweepSchema.safeParse({ ...manualPower,
    cells: [{ ...referenceCell, band_reference }] }).success).toBe(false)
})
test.each([null, undefined])('preserves historical band reference/share absence or null: %s', (value) => {
  const historical = value === undefined ? referenceCell : { ...referenceCell, band_reference: null, deviation_share: null }
  const parsed = powerSweepSchema.parse({ ...manualPower, cells: [historical] })
  if (value === undefined) {
    expect(parsed).not.toHaveProperty('band_reference')
    expect(parsed.cells[0]).not.toHaveProperty('band_reference')
    expect(parsed.cells[0]).not.toHaveProperty('deviation_share')
  } else expect(parsed.cells[0]).toMatchObject({ band_reference: null, deviation_share: null })
})
test('band transport preserves values without shadow scientific validation', () => {
  expect(powerSweepSchema.parse({ ...manualPower, band_reference: null,
    cells: [{ ...referenceCell, band_reference: bandReference, half_life: -1, deviation_share: 2 }] })
    .cells[0]).toMatchObject({ band_reference: bandReference, half_life: -1, deviation_share: 2 })
})


// ADR-322: attribution and pairing are part of the wire contract, not inferred from scores.
const measuredCrossSectional = {
  created_at: '2026-10-19T10:00:00Z',
  universe_size: 3,
  graduated: false,
  trials: [0, -0.37].map((score, index) => ({
    strategy_name: `family_${index}`,
    observed_sharpe: 0.5,
    deflated_sharpe: -0.08,
    pbo: 0.44,
    parameter_stability_score: 0.22,
    walk_forward_oos_sharpe: score,
  })),
  walk_forward_method: 'family-walk-forward-equal-weight-continuation-v1',
  walk_forward_hold_sharpe: -0.12,
  walk_forward_n_bars: 60,
  walk_forward_n_splits: 3,
}

test('cross-sectional attribution preserves paired scores, zero and actual geometry', () => {
  const parsed = crossSectionalResponseSchema.parse(measuredCrossSectional)
  expect(parsed).toEqual(measuredCrossSectional)
})

test.each([undefined, null])('cross-sectional legacy metadata %s preserves an unpaired scalar', (method) => {
  const legacy = {
    ...measuredCrossSectional,
    walk_forward_method: method,
    walk_forward_hold_sharpe: null,
    walk_forward_n_bars: null,
    walk_forward_n_splits: null,
  }
  expect(crossSectionalResponseSchema.parse(legacy)).toEqual(legacy)
})

test.each([
  { walk_forward_method: 'unknown' },
  { walk_forward_hold_sharpe: null },
  { walk_forward_hold_sharpe: undefined },
  { walk_forward_hold_sharpe: Infinity },
  { walk_forward_hold_sharpe: NaN },
  { walk_forward_n_bars: null },
  { walk_forward_n_bars: undefined },
  { walk_forward_n_bars: true },
  { walk_forward_n_bars: 60.5 },
  { walk_forward_n_bars: Infinity },
  { walk_forward_n_bars: Number.MAX_SAFE_INTEGER + 1 },
  { walk_forward_n_bars: 3 },
  { walk_forward_n_splits: null },
  { walk_forward_n_splits: undefined },
  { walk_forward_n_splits: false },
  { walk_forward_n_splits: 1.5 },
  { walk_forward_n_splits: 0 },
  { walk_forward_n_splits: -1 },
  { walk_forward_n_splits: Number.MAX_SAFE_INTEGER + 1 },
  { trials: [] },
])('cross-sectional measured contract refuses malformed metadata %j', (patch) => {
  expect(crossSectionalResponseSchema.safeParse({ ...measuredCrossSectional, ...patch }).success).toBe(false)
})

test.each([undefined, null, NaN, Infinity, -Infinity])(
  'cross-sectional measured contract refuses missing/nonfinite family mean %s',
  (score) => {
    const trials = measuredCrossSectional.trials.map((trial, index) =>
      index === 1 ? { ...trial, walk_forward_oos_sharpe: score } : trial,
    )
    expect(crossSectionalResponseSchema.safeParse({ ...measuredCrossSectional, trials }).success).toBe(false)
  },
)

test.each(['walk_forward_hold_sharpe', 'walk_forward_n_bars', 'walk_forward_n_splits'] as const)(
  'cross-sectional legacy contract refuses orphan %s',
  (field) => {
    const legacy = {
      ...measuredCrossSectional,
      walk_forward_method: null,
      walk_forward_hold_sharpe: null,
      walk_forward_n_bars: null,
      walk_forward_n_splits: null,
      [field]: measuredCrossSectional[field],
    }
    expect(crossSectionalResponseSchema.safeParse(legacy).success).toBe(false)
  },
)

test.each([Infinity, -Infinity, NaN])('cross-sectional legacy scalar must also be finite: %s', (score) => {
  const legacy = {
    ...measuredCrossSectional,
    walk_forward_method: null,
    walk_forward_hold_sharpe: null,
    walk_forward_n_bars: null,
    walk_forward_n_splits: null,
    trials: [{ ...measuredCrossSectional.trials[0], walk_forward_oos_sharpe: score }],
  }
  expect(crossSectionalResponseSchema.safeParse(legacy).success).toBe(false)
})

// ADR-328: validate published structure without deriving scores or the server verdict.
const pcvEvidence = {
  method: 'restricted-shift-family-purged-equal-weight-continuation-v1',
  status: 'measured', n_bars: 60, requested_folds: 3, floor: 0,
  reason: null, dependency_rule: 'shifted-reversal-v1', max_price_lag: 4,
  embargo: 4, kept_fold_ordinals: [0, 1, 2], mean_oos_sharpe: 0,
  mean_oos_hold_sharpe: -0.12,
}
const pcvView = (evidence: Record<string, unknown> | null = pcvEvidence, scalar: unknown = 0) => ({
  created_at: '2026-10-20T10:00:00Z', universe_size: 3, graduated: false,
  trials: [{ strategy_name: 'xs_reversal', observed_sharpe: 1, deflated_sharpe: 1,
    pbo: 0, parameter_stability_score: 1, purged_cv_oos_sharpe: scalar,
    purged_diagnostic: evidence }],
})

test('PCV preserves exact current evidence and trusts the supplied graduation verdict', () => {
  expect(crossSectionalResponseSchema.parse(pcvView())).toEqual(pcvView())
})

test.each([undefined, null, 0, -0.37])('PCV absent historical evidence preserves scalar %s', (scalar) => {
  const view = pcvView(null, scalar)
  expect(crossSectionalResponseSchema.parse(view)).toEqual(view)
})

test.each([Infinity, -Infinity, NaN])('PCV historical scalar refuses nonfinite %s', (scalar) => {
  expect(crossSectionalResponseSchema.safeParse(pcvView(null, scalar)).success).toBe(false)
})

const unsupportedPcv = { ...pcvEvidence, status: 'unsupported', reason: 'unsupported_factory',
  dependency_rule: null, max_price_lag: null, embargo: null, kept_fold_ordinals: null,
  mean_oos_sharpe: null, mean_oos_hold_sharpe: null }
const emptyPcv = { ...pcvEvidence, status: 'no_usable_folds', max_price_lag: 60,
  embargo: 60, kept_fold_ordinals: [], mean_oos_sharpe: null, mean_oos_hold_sharpe: null }

test.each([unsupportedPcv, emptyPcv])('PCV preserves current unmeasured states $status', (evidence) => {
  const view = pcvView(evidence, null)
  expect(crossSectionalResponseSchema.parse(view)).toEqual(view)
})

test.each([
  { method: 'other' }, { status: 'other' }, { reason: 'unsupported_factory' },
  { dependency_rule: 'other' }, { dependency_rule: null }, { max_price_lag: null },
  { embargo: null }, { kept_fold_ordinals: null }, { mean_oos_sharpe: null },
  { mean_oos_hold_sharpe: null }, { mean_oos_sharpe: Infinity },
  { mean_oos_hold_sharpe: NaN }, { n_bars: 2 }, { requested_folds: 1 },
  { n_bars: true }, { requested_folds: 3.1 }, { floor: false }, { floor: -1 },
  { max_price_lag: 0 }, { embargo: 3 }, { embargo: 5 },
  { n_bars: Number.MAX_SAFE_INTEGER + 1 }, { floor: Number.MAX_SAFE_INTEGER + 1 },
  { requested_folds: Number.MAX_SAFE_INTEGER + 1 },
  { max_price_lag: Number.MAX_SAFE_INTEGER + 1 }, { embargo: Number.MAX_SAFE_INTEGER + 1 },
  { kept_fold_ordinals: [] }, { kept_fold_ordinals: [0, 1] },
  { kept_fold_ordinals: [0, 1, 2, 3] }, { kept_fold_ordinals: [0, 0, 2] },
  { kept_fold_ordinals: [1, 0, 2] }, { kept_fold_ordinals: [-1, 1, 2] },
  { kept_fold_ordinals: [0, 1, 3] }, { kept_fold_ordinals: [0, 1, 1.5] },
  { kept_fold_ordinals: [0, 1, true] },
  { kept_fold_ordinals: [0, 1, Number.MAX_SAFE_INTEGER + 1] },
])('PCV rejects measured contradiction %j without WF attribution', (patch) => {
  expect(crossSectionalResponseSchema.safeParse(pcvView({ ...pcvEvidence, ...patch })).success).toBe(false)
})

test.each([
  { reason: null }, { reason: 'other' }, { dependency_rule: 'shifted-reversal-v1' },
  { max_price_lag: 4 }, { embargo: 4 }, { kept_fold_ordinals: [] },
  { mean_oos_sharpe: 0 }, { mean_oos_hold_sharpe: 0 },
])('PCV rejects unsupported contradiction %j', (patch) => {
  expect(crossSectionalResponseSchema.safeParse(pcvView({ ...unsupportedPcv, ...patch }, null)).success).toBe(false)
})

test.each([
  { kept_fold_ordinals: [0] }, { mean_oos_sharpe: 0 }, { mean_oos_hold_sharpe: 0 },
  { reason: 'unsupported_factory' }, { dependency_rule: null }, { embargo: 4, max_price_lag: 4 },
])('PCV rejects no-fold contradiction %j', (patch) => {
  expect(crossSectionalResponseSchema.safeParse(pcvView({ ...emptyPcv, ...patch }, null)).success).toBe(false)
})

test.each([null, undefined, 0.01])('PCV binds measured scalar %s', (scalar) => {
  const view = pcvView()
  view.trials[0].purged_cv_oos_sharpe = scalar
  expect(crossSectionalResponseSchema.safeParse(view).success).toBe(false)
})

test.each([unsupportedPcv, emptyPcv])('PCV unmeasured evidence refuses nonnull scalar $status', (evidence) => {
  expect(crossSectionalResponseSchema.safeParse(pcvView(evidence, 0)).success).toBe(false)
})

test('PCV permits distinct family geometry and benchmarks with one common request', () => {
  const view = pcvView()
  const second = { ...view.trials[0], strategy_name: 'xs_momentum', purged_cv_oos_sharpe: -0.3,
    purged_diagnostic: { ...pcvEvidence, dependency_rule: 'shifted-momentum-v1',
      max_price_lag: 30, embargo: 30, kept_fold_ordinals: [0, 2],
      mean_oos_sharpe: -0.3, mean_oos_hold_sharpe: 0.7 } }
  const distinct = { ...view, trials: [...view.trials, second] }
  expect(crossSectionalResponseSchema.parse(distinct)).toEqual(distinct)
})

test.each([null, { ...pcvEvidence, n_bars: 61 }, { ...pcvEvidence, requested_folds: 2,
  kept_fold_ordinals: [0, 1] }, { ...pcvEvidence, floor: 1 }])(
  'PCV requires complete common request even when WF method is null: %j', (evidence) => {
    const view = pcvView()
    const trials = [...view.trials, { ...view.trials[0], strategy_name: 'second', purged_diagnostic: evidence }]
    expect(crossSectionalResponseSchema.safeParse({ ...view, walk_forward_method: null, trials }).success).toBe(false)
  },
)

test.each([60, 61])('PCV binds search bars to attributed WF: %s', (bars) => {
  const view = { ...measuredCrossSectional, trials: measuredCrossSectional.trials.map((trial) => ({
    ...trial, purged_cv_oos_sharpe: 0, purged_diagnostic: { ...pcvEvidence, n_bars: bars },
  })) }
  expect(crossSectionalResponseSchema.safeParse(view).success).toBe(bars === 60)
})

test('PCV compact geometry agrees with exhaustive small direct fold enumeration', () => {
  for (let bars = 2; bars <= 24; bars++) {
    for (let folds = 2; folds <= bars; folds++) {
      for (let embargo = 1; embargo <= bars + 1; embargo++) {
        const q = Math.floor(bars / folds), remainder = bars % folds
        const kept = Array.from({ length: folds }, (_, j) => j).filter((j) => {
          const start = q * j + Math.min(j, remainder)
          const end = start + q + Number(j < remainder)
          return start > embargo || end + embargo < bars
        })
        const evidence = { ...pcvEvidence, n_bars: bars, requested_folds: folds,
          floor: embargo, max_price_lag: 1, embargo, kept_fold_ordinals: kept,
          status: kept.length ? 'measured' : 'no_usable_folds',
          mean_oos_sharpe: kept.length ? 0 : null, mean_oos_hold_sharpe: kept.length ? -0.12 : null }
        expect(crossSectionalResponseSchema.safeParse(pcvView(evidence, kept.length ? 0 : null)).success).toBe(true)
        const forged = { ...evidence, kept_fold_ordinals: kept.length ? kept.slice(1) : [0] }
        expect(crossSectionalResponseSchema.safeParse(pcvView(forged, kept.length ? 0 : null)).success).toBe(false)
      }
    }
  }
})

test('PCV exact geometry handles MAX_SAFE counts and overflowing intermediate sums without allocations', () => {
  const max = Number.MAX_SAFE_INTEGER
  const evidence = { ...emptyPcv, n_bars: max, requested_folds: max, floor: max - 1,
    max_price_lag: 1, embargo: max - 1 }
  expect(crossSectionalResponseSchema.parse(pcvView(evidence, null))).toEqual(pcvView(evidence, null))
  // Fold 0 ends at 3002399751580331. Exact end + E equals N, so only
  // the last fold has training. Increasing E by one removes that last fold too.
  const thirds = { ...emptyPcv, n_bars: max, requested_folds: 3,
    floor: 6004799503160660, max_price_lag: 1, embargo: 6004799503160660,
    status: 'measured', kept_fold_ordinals: [2], mean_oos_sharpe: 0, mean_oos_hold_sharpe: -0.12 }
  expect(crossSectionalResponseSchema.parse(pcvView(thirds))).toEqual(pcvView(thirds))
  const noThirds = { ...emptyPcv, n_bars: max, requested_folds: 3,
    floor: 6004799503160661, max_price_lag: 1, embargo: 6004799503160661 }
  expect(crossSectionalResponseSchema.parse(pcvView(noThirds, null))).toEqual(pcvView(noThirds, null))
})

test('PCV rejects wrong kept membership even when cardinality, sorting and range match', () => {
  const evidence = { ...pcvEvidence, max_price_lag: 30, embargo: 30, kept_fold_ordinals: [0, 1] }
  expect(crossSectionalResponseSchema.safeParse(pcvView(evidence)).success).toBe(false)
})

test('PCV measured branch cannot claim a mean when exact geometry retains no folds', () => {
  expect(crossSectionalResponseSchema.safeParse(pcvView({ ...emptyPcv,
    status: 'measured', mean_oos_sharpe: 0, mean_oos_hold_sharpe: 0 })).success).toBe(false)
})

test('PCV count integrity concerns parsed JavaScript values, not original JSON numeric spelling', () => {
  const raw = JSON.stringify(pcvView()).replace('"n_bars":60', '"n_bars":60.000000000000001')
  // response.json() has already rounded this token to the safe integer 60. A structural
  // Zod boundary cannot recover or certify the token's original spelling/integrality.
  expect(crossSectionalResponseSchema.parse(JSON.parse(raw))).toEqual(pcvView())
})

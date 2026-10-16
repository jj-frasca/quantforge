import type { CalibrationCompatibility as Compatibility } from '../../types/lab'

const messages = {
  MATCHED: 'Matches current default.',
  DIFFERENT: 'Different procedure or history.',
  UNKNOWN: 'Current default comparison unknown.',
}
const states = { MATCHED: 'matched', DIFFERENT: 'different', UNKNOWN: 'unknown' }

type RecordedIdentity = {
  label: string
  search_config_version: string
  gate_config_version: string
}

export function CalibrationCompatibility({ compatibility, recorded }: {
  compatibility?: Compatibility | null
  recorded: RecordedIdentity[]
}) {
  const reference = compatibility?.reference
  return (
    <div aria-label="current default comparison" style={{ minWidth: '16rem', maxWidth: '28rem', overflowWrap: 'anywhere', textAlign: 'left' }}>
      <p>{messages[compatibility?.status ?? 'UNKNOWN']}</p>
      <p>
        Search: {states[compatibility?.search ?? 'UNKNOWN']}; gate: {states[compatibility?.gate ?? 'UNKNOWN']};
        {' '}history: {states[compatibility?.history ?? 'UNKNOWN']}.
      </p>
      <p>{reference
        ? `Current default target: ${reference.n_bars.toLocaleString('en-US')} bars.`
        : 'Current default reference unavailable.'}</p>
      <details>
        <summary>Recorded and current settings</summary>
        <p>Procedure and history comparison only. Results describe the recorded simulated run and do not guarantee performance in real markets.</p>
        {compatibility?.reasons.map((reason, index) => <p key={index}>{reason}</p>)}
        {recorded.map((identity, index) => (
          <div key={index}>
            <p>Recorded run: {identity.label}</p>
            <p>Recorded search: <code>{identity.search_config_version}</code></p>
            <p>Recorded gate: <code>{identity.gate_config_version}</code></p>
          </div>
        ))}
        {reference && <div>
          <p>Current default search: <code>{reference.search_config_version}</code></p>
          <p>Current default gate: <code>{reference.gate_config_version}</code></p>
          <p>Current default strategies: {reference.strategy_names.join(', ')}</p>
          <p>Grid points per parameter: {reference.n_per_param}; refinement: {reference.refine ? 'enabled' : 'disabled'};
            {' '}refinement span: {reference.refine_span}; selection: {reference.select_by}.</p>
        </div>}
      </details>
    </div>
  )
}

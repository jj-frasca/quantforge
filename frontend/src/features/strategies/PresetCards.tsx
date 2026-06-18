import { PRESETS, type Preset } from './presets'

interface Props {
  onLoad: (preset: Preset) => void
}

export function PresetCards({ onLoad }: Props) {
  return (
    <section aria-label="Try these first" className="preset-cards">
      <h3 className="preset-cards-heading">Try one of these first</h3>
      <ul className="preset-cards-grid">
        {PRESETS.map((preset) => (
          <li key={preset.id}>
            <article className="preset-card" aria-labelledby={`preset-${preset.id}-title`}>
              <h4 id={`preset-${preset.id}-title`}>{preset.title}</h4>
              <p className="preset-card-subtitle">{preset.subtitle}</p>
              <p className="preset-card-description">{preset.description}</p>
              <button
                type="button"
                className="preset-card-load"
                onClick={() => onLoad(preset)}
              >
                Load this preset
              </button>
            </article>
          </li>
        ))}
      </ul>
    </section>
  )
}

import { useState } from 'react'

export const ONBOARDING_DISMISSED_KEY = 'quantforge.onboarding.dismissed'

// Read the persisted dismissal flag at mount time. localStorage is sync and lives on
// `window`, which jsdom provides for tests — no need to gate on `typeof window`.
const wasDismissed = (): boolean =>
  window.localStorage.getItem(ONBOARDING_DISMISSED_KEY) === '1'

interface Step {
  title: string
  body: string
}

// No exact strategy count here on purpose (this used to say "Eleven" and drifted stale
// as the catalog grew to 34+ unnoticed for months) -- this banner has no live catalog
// data of its own, and it's rendered on every page, so it isn't worth wiring in a fetch
// just to keep a number current.
const STEPS: readonly Step[] = [
  { title: 'Pick a strategy', body: 'A library of built-in setups grouped by category.' },
  { title: 'Adjust if you want', body: 'Every field is pre-filled with sensible defaults.' },
  { title: 'See the result', body: 'Equity curve, drawdowns, and validation in one click.' },
]

export function OnboardingBanner() {
  const [dismissed, setDismissed] = useState(wasDismissed)

  if (dismissed) return null

  const onDismiss = () => {
    window.localStorage.setItem(ONBOARDING_DISMISSED_KEY, '1')
    setDismissed(true)
  }

  return (
    <section
      role="region"
      aria-label="Getting started"
      className="onboarding-banner"
    >
      <div className="onboarding-banner-header">
        <h2>New here? Three steps.</h2>
        <button
          type="button"
          className="onboarding-banner-dismiss"
          onClick={onDismiss}
        >
          Got it
          <span aria-hidden="true"> ✕</span>
        </button>
      </div>
      <ol className="onboarding-banner-steps">
        {STEPS.map((step, i) => (
          <li key={step.title}>
            <span className="onboarding-banner-step-num">{i + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <span className="onboarding-banner-step-body"> — {step.body}</span>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

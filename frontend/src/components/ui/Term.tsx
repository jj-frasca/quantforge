import type { ReactNode } from 'react'

interface Props {
  /**
   * Plain-English explanation shown on hover/focus. Should read as a complete sentence;
   * the caller is responsible for keeping it brief enough to fit in a small tooltip.
   */
  definition: string
  /** The jargon term (the visible text). */
  children: ReactNode
}

/**
 * A jargon term with an inline plain-English definition. Underlined so a beginner knows
 * something explains itself; the tooltip appears on hover (mouse) and on focus (keyboard
 * / touch — `tabIndex={0}` makes the element focusable). Reusable so every PBO / Sharpe /
 * drawdown in the app gets the same affordance and we never have to teach jargon twice.
 *
 * Implementation note: the tooltip is a `<span>` rendered next to the term and toggled by
 * CSS (`.term-tooltip`) — no JS state needed. The browser-native `title` attribute is
 * also set as a fallback for screen readers / unstyled environments.
 */
export function Term({ definition, children }: Props) {
  return (
    <span className="term" tabIndex={0} title={definition}>
      {children}
      <span role="tooltip" className="term-tooltip">
        {definition}
      </span>
    </span>
  )
}

import { CrossSectionalPanel } from './CrossSectionalPanel'
import { GraduatesPanel } from './GraduatesPanel'

export function DiscoveriesPage() {
  return (
    <section aria-label="discoveries page" className="page lab-dashboard">
      <header>
        <h2>Discoveries</h2>
        <p>
          The strategies the autonomous lab has actually found. Graduates cleared the full
          per-symbol gate; the cross-sectional hunt ranks a dollar-neutral edge across the whole
          universe. Both carry their honest deflation caveats.
        </p>
      </header>

      <GraduatesPanel />
      <CrossSectionalPanel />
    </section>
  )
}

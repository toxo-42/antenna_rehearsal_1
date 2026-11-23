import { EmptyNotice, SourceBadge } from './Badges.tsx'
import { antennaText, timeText } from './labels.ts'
import { S11Chart } from './S11Chart.tsx'
import type { Measurement, Remeasure } from './types.ts'
import { VerdictCard } from './VerdictCard.tsx'

interface CardPageProps {
  measurement: Measurement | null
  emptyText: string
  onRemeasure?: (remeasure: Remeasure) => void
}

/** Screen 2: the graph and the verdict card of one measurement. */
export function CardPage(props: CardPageProps) {
  const { measurement } = props
  if (measurement === null) return <EmptyNotice>{props.emptyText}</EmptyNotice>
  return (
    <div className="page">
      <header className="page-head page-head-row">
        <h1>{measurement.antenna.name}</h1>
        <span className="muted">{antennaText(measurement.antenna)}</span>
        <SourceBadge source={measurement.source} />
        <span className="muted">{timeText(measurement.measured_at)}</span>
      </header>
      <div className="columns">
        <section className="card column">
          <h2>
            S11 그래프 <SourceBadge source={measurement.source} />
          </h2>
          <S11Chart measurement={measurement} />
        </section>
        <div className="column">
          <VerdictCard
            key={measurement.id}
            card={measurement.card}
            measurementId={measurement.id}
            onRemeasure={props.onRemeasure}
          />
        </div>
      </div>
    </div>
  )
}

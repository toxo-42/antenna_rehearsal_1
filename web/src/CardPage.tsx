import { EmptyNotice, SourceBadge } from './Badges.tsx'
import { antennaText, timeText } from './labels.ts'
import { S11Chart } from './S11Chart.tsx'
import type { Measurement } from './types.ts'
import { VerdictCard } from './VerdictCard.tsx'

/** Screen 2: the graph and the verdict card of one measurement. */
export function CardPage({ measurement }: { measurement: Measurement | null }) {
  if (measurement === null) {
    return <EmptyNotice>아직 측정이 없습니다. ① 측정에서 시작하거나 ③ 이력에서 골라 주세요.</EmptyNotice>
  }
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
          <VerdictCard key={measurement.id} card={measurement.card} measurementId={measurement.id} />
        </div>
      </div>
    </div>
  )
}

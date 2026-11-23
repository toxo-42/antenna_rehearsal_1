import { EmptyNotice, SourceBadge } from './Badges.tsx'
import { antennaText, timeText } from './labels.ts'
import { NextMeasureBar } from './NextMeasureBar.tsx'
import { S11Chart } from './S11Chart.tsx'
import type { Measurement, Remeasure } from './types.ts'
import type { MeasureState } from './useAppState.ts'
import { VerdictCard } from './VerdictCard.tsx'

/** What the screen needs to measure again. Left out where measuring is hidden (demo mode). */
export interface Again {
  measure: MeasureState
  onRemeasure: (remeasure: Remeasure) => void
  onGoMeasure: () => void
}

interface CardPageProps {
  measurement: Measurement | null
  emptyText: string
  again?: Again
}

/** Screen 2: the graph and the verdict card of one measurement, then the next measurement. */
export function CardPage({ measurement, emptyText, again }: CardPageProps) {
  if (measurement === null) return <EmptyNotice>{emptyText}</EmptyNotice>
  return (
    <div className="page">
      <header className="page-head page-head-row">
        <h1>판정</h1>
        <span>
          {measurement.antenna.name} · {antennaText(measurement.antenna)}
        </span>
        <SourceBadge source={measurement.source} />
        <span>{timeText(measurement.measured_at)}</span>
      </header>
      <div className="verdict-layout">
        <section className="card chart-card">
          <h2>S11 그래프</h2>
          <S11Chart measurement={measurement} />
        </section>
        <VerdictCard
          key={measurement.id}
          card={measurement.card}
          kind={measurement.antenna.kind}
          measurementId={measurement.id}
          onRemeasure={again?.onRemeasure}
        />
      </div>
      {again !== undefined && (
        <NextMeasureBar antenna={measurement.antenna} measure={again.measure} onGoMeasure={again.onGoMeasure} />
      )}
    </div>
  )
}

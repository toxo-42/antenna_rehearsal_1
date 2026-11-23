import { useState } from 'react'
import { AssistBoxes } from './AssistBoxes.tsx'
import { StageChip } from './Badges.tsx'
import { stageTone } from './labels.ts'
import type { Card, Diagnosis, Remeasure } from './types.ts'

interface VerdictProps {
  card: Card
  measurementId: number
  /** Fills the USB range boxes and opens the measure tab. Left out where measuring is hidden. */
  onRemeasure?: (remeasure: Remeasure) => void
}

/**
 * The verdict card. Every sentence and number is the server's string, shown as it is.
 * Order: headline -> diagnoses (title, action, evidence, guide) -> status.
 */
export function VerdictCard({ card, measurementId, onRemeasure }: VerdictProps) {
  const again = card.remeasure ?? null
  return (
    <section className={`card verdict tone-border-${stageTone(card.stage)}`} aria-label="판정 카드">
      <div className="verdict-headline">
        <StageChip stage={card.stage} />
        <h2>{card.headline}</h2>
      </div>
      {card.diagnoses.length > 0 && <Diagnoses diagnoses={card.diagnoses} />}
      {again !== null && (
        <div className="verdict-remeasure" role="note">
          <p className="explain-warning">{again.note}</p>
          {onRemeasure !== undefined && (
            <button type="button" className="button-secondary" onClick={() => onRemeasure(again)}>
              이 범위를 USB 측정 칸에 채우기 →
            </button>
          )}
        </div>
      )}
      {card.status.length > 0 && (
        <div className="verdict-status">
          <h3>측정값</h3>
          <ul>
            {card.status.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      <AssistBoxes measurementId={measurementId} />
    </section>
  )
}

/** One cause at a time, so a beginner reads them in order. */
function Diagnoses({ diagnoses }: { diagnoses: Diagnosis[] }) {
  const [index, setIndex] = useState(0)
  const shown = diagnoses[Math.min(index, diagnoses.length - 1)]
  return (
    <div className="verdict-diagnoses">
      <div className="row-between">
        <h3>원인과 할 일</h3>
        <span className="muted-strong">
          {index + 1} / {diagnoses.length}
        </span>
      </div>
      <article className="diagnosis">
        <h4>{shown.title}</h4>
        <dl>
          <dt>할 일</dt>
          <dd>{shown.action}</dd>
          <dt>근거</dt>
          <dd>{shown.evidence}</dd>
          <dt>설명</dt>
          <dd>{shown.guide}</dd>
        </dl>
      </article>
      {diagnoses.length > 1 && <Pager index={index} count={diagnoses.length} onMove={setIndex} />}
    </div>
  )
}

function Pager({ index, count, onMove }: { index: number; count: number; onMove: (index: number) => void }) {
  return (
    <div className="row-between">
      <button type="button" className="button-secondary" disabled={index === 0} onClick={() => onMove(index - 1)}>
        ← 이전 원인
      </button>
      <button
        type="button"
        className="button-secondary"
        disabled={index >= count - 1}
        onClick={() => onMove(index + 1)}
      >
        다음 원인 →
      </button>
    </div>
  )
}


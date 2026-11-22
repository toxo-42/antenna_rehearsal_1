import { useState } from 'react'
import { StageChip } from './Badges.tsx'
import { stageTone } from './labels.ts'
import type { Card, Diagnosis } from './types.ts'

/**
 * The verdict card. Every sentence and number is the server's string, shown as it is.
 * Order: headline -> diagnoses (title, action, evidence, guide) -> status.
 */
export function VerdictCard({ card }: { card: Card }) {
  return (
    <section className={`card verdict tone-border-${stageTone(card.stage)}`} aria-label="판정 카드">
      <div className="verdict-headline">
        <StageChip stage={card.stage} />
        <h2>{card.headline}</h2>
      </div>
      {card.diagnoses.length > 0 && <Diagnoses diagnoses={card.diagnoses} />}
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
      <ExplainBox />
      <AskBox />
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

/** Place for the plain-language explanation. It is connected in P5 and stays disabled until then. */
function ExplainBox() {
  return (
    <div className="ask">
      <button type="button" disabled>
        쉬운 말로 설명 듣기
      </button>
      <p className="ask-answer">
        <span className="ai-tag">AI 설명(참고용)</span> 풀어 쓴 글은 이 표시와 함께 여기에 나옵니다
      </p>
    </div>
  )
}

/** Place for the question box. It is connected in P5 and stays disabled until then. */
function AskBox() {
  return (
    <div className="ask">
      <h3>
        <label htmlFor="ask-input">질문하기</label>
      </h3>
      <div className="ask-row">
        <input id="ask-input" type="text" placeholder="아직 연결되지 않았습니다" disabled />
        <button type="button" disabled>
          질문하기
        </button>
      </div>
      <p className="ask-answer">
        <span className="ai-tag">AI가 고른 설명</span> 답은 이 표시와 함께 여기에 나옵니다
      </p>
    </div>
  )
}

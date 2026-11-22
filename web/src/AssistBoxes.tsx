import { useState } from 'react'
import type { FormEvent } from 'react'
import { askQuestion, describeError, explainMeasurement, getHealth, listGuides } from './api.ts'
import type { ErrorInfo } from './api.ts'
import { ErrorNotice, LoadingNotice } from './Badges.tsx'
import {
  ASK_NOT_IN_CARD,
  EXPLAIN_LABEL,
  askNotice,
  explainNotice,
  explanationBlocks,
  warningText,
} from './explainText.ts'
import type { AskAnswer, Explanation, Health } from './types.ts'
import { useLoad } from './useLoad.ts'

const MAX_QUESTION = 200

type Call<T> =
  | { status: 'idle' }
  | { status: 'busy' }
  | { status: 'error'; error: ErrorInfo }
  | { status: 'done'; data: T }

/** One request started by a click. The card is keyed by measurement, so a new card starts idle. */
function useCall<T>(): [Call<T>, (run: () => Promise<T>) => void] {
  const [call, setCall] = useState<Call<T>>({ status: 'idle' })
  const start = (run: () => Promise<T>) => {
    setCall({ status: 'busy' })
    run().then(
      (data) => setCall({ status: 'done', data }),
      (error: unknown) => setCall({ status: 'error', error: describeError(error) }),
    )
  }
  return [call, start]
}

/** The two local-model helpers under the card. Nothing here changes the card above. */
export function AssistBoxes({ measurementId }: { measurementId: number }) {
  const [health] = useLoad(getHealth, 'health')
  if (health.status !== 'ready') return null
  return (
    <>
      {health.data.explain && <ExplainBox measurementId={measurementId} />}
      <AskBox measurementId={measurementId} health={health.data} />
    </>
  )
}

function ExplainBox({ measurementId }: { measurementId: number }) {
  const [call, start] = useCall<Explanation>()
  if (call.status === 'done' && call.data.status === 'off') return null
  return (
    <div className="ask">
      <button
        type="button"
        disabled={call.status === 'busy'}
        onClick={() => start(() => explainMeasurement(measurementId))}
      >
        쉬운 말로 설명 듣기
      </button>
      {call.status === 'busy' && (
        <p className="ask-answer" role="status">
          <progress /> AI 설명을 만드는 중입니다. 컴퓨터에 따라 1~2분 걸릴 수 있습니다.
        </p>
      )}
      {call.status === 'error' && <ErrorNotice error={call.error} />}
      {call.status === 'done' && <ExplainResult result={call.data} />}
    </div>
  )
}

function ExplainResult({ result }: { result: Explanation }) {
  const notice = explainNotice(result.status)
  if (notice !== null || result.text === null) return <p className="ask-answer">{notice}</p>
  const warning = warningText(result.warnings)
  return (
    <div className="explain">
      <p className="ask-answer">
        <span className="ai-tag">{EXPLAIN_LABEL}</span> {result.model} · {result.seconds}초
      </p>
      {warning !== null && <p className="explain-warning">△ {warning}</p>}
      {explanationBlocks(result.text).map((block, index) => {
        if (block.kind === 'heading') return <h4 key={index}>{block.text}</h4>
        if (block.kind === 'paragraph') return <p key={index}>{block.text}</p>
        return (
          <ol key={index} start={block.start}>
            {block.items.map((item, itemIndex) => (
              <li key={itemIndex}>{item}</li>
            ))}
          </ol>
        )
      })}
    </div>
  )
}

function AskBox({ measurementId, health }: { measurementId: number; health: Health }) {
  if (health.ollama) return <QuestionForm measurementId={measurementId} />
  return (
    <div className="ask">
      <h3>설명 목록에서 고르기</h3>
      <GuidePicker measurementId={measurementId} />
    </div>
  )
}

/** An answer is shown only while the box still holds the question it answers. */
function QuestionForm({ measurementId }: { measurementId: number }) {
  const [question, setQuestion] = useState('')
  const [asked, setAsked] = useState<string | null>(null)
  const [call, start] = useCall<AskAnswer>()
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (question.trim() === '') return
    setAsked(question)
    start(() => askQuestion(measurementId, question))
  }
  const current = asked === question
  return (
    <form className="ask" onSubmit={submit}>
      <QuestionInput question={question} busy={call.status === 'busy'} onChange={setQuestion} />
      {current && call.status === 'busy' && <LoadingNotice />}
      {current && call.status === 'error' && <ErrorNotice error={call.error} />}
      {current && call.status === 'done' && (
        <AskResult answer={call.data} measurementId={measurementId} />
      )}
    </form>
  )
}

interface QuestionInputProps {
  question: string
  busy: boolean
  onChange: (question: string) => void
}

function QuestionInput({ question, busy, onChange }: QuestionInputProps) {
  return (
    <>
      <h3>
        <label htmlFor="ask-input">질문하기</label>
      </h3>
      <div className="ask-row">
        <input
          id="ask-input"
          type="text"
          maxLength={MAX_QUESTION}
          placeholder="예: 선이 너무 길면 주파수가 어떻게 돼요?"
          value={question}
          onChange={(event) => onChange(event.target.value)}
        />
        <button type="submit" disabled={busy || question.trim() === ''}>
          질문하기
        </button>
      </div>
      <small>
        {question.length} / {MAX_QUESTION}자
      </small>
    </>
  )
}

function AskResult({ answer, measurementId }: { answer: AskAnswer; measurementId: number }) {
  const notice = askNotice(answer.status)
  if (notice !== null || answer.guide === null) {
    return (
      <>
        <p className="ask-answer">{notice}</p>
        {answer.status === 'failed' && <GuidePicker measurementId={measurementId} />}
      </>
    )
  }
  return (
    <div className="ask-result">
      <p>
        <span className="ai-tag">AI가 고른 설명</span> {answer.guide}
      </p>
      <InCard inCard={answer.in_card} action={answer.action} />
    </div>
  )
}

function InCard({ inCard, action }: { inCard: boolean; action: string | null }) {
  if (inCard && action !== null) return <p className="muted-strong">이번 카드의 할 일: {action}</p>
  return <p className="muted">{ASK_NOT_IN_CARD}</p>
}

/** Every verified guide grouped by topic, for picking by hand. */
function GuidePicker({ measurementId }: { measurementId: number }) {
  const [guides, reload] = useLoad(() => listGuides(measurementId), measurementId)
  if (guides.status === 'loading') return <LoadingNotice />
  if (guides.status === 'error') return <ErrorNotice error={guides.error} onRetry={reload} />
  return (
    <div className="guide-picker">
      {guides.data.map((topic) => (
        <details key={topic.topic}>
          <summary>{topic.topic}</summary>
          <ul>
            {topic.items.map((item) => (
              <li key={item.key}>
                <p>{item.guide}</p>
                <InCard inCard={item.in_card} action={item.action} />
              </li>
            ))}
          </ul>
        </details>
      ))}
    </div>
  )
}

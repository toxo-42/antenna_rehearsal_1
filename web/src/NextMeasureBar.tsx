import { ErrorNotice } from './Badges.tsx'
import { ChangeNoteFields } from './ChangeNoteFields.tsx'
import { LengthField } from './LengthField.tsx'
import { nextMeasureView } from './nextMeasure.ts'
import type { BarAction } from './nextMeasure.ts'
import type { Antenna } from './types.ts'
import type { MeasureState } from './useAppState.ts'

interface BarProps {
  antenna: Antenna
  measure: MeasureState
  onGoMeasure: () => void
}

/**
 * Under the verdict: note what was changed and measure again without leaving the screen.
 * Nothing is measured until the student presses the button. What is shown is decided in
 * nextMeasure.ts.
 */
export function NextMeasureBar({ antenna, measure, onGoMeasure }: BarProps) {
  const { lastPort, usbRange, busy, changeNote } = measure
  const view = nextMeasureView({ kind: antenna.kind, lastPort, boxes: usbRange, busy, changeNote })
  return (
    <section className="card next-measure" aria-label="다음 측정">
      {measure.error !== null && <ErrorNotice error={measure.error} />}
      {busy && (
        <p className="notice" role="status">
          측정하는 중…
        </p>
      )}
      <div className="next-measure-row">
        <div>
          <h2>다음 측정</h2>
          <small>고친 내용을 적고 다시 측정합니다</small>
        </div>
        {view.showLength && <LengthField measure={measure} />}
        <div className="field-stack">
          <ChangeNoteFields measure={measure} />
          <small>{view.savedText}</small>
        </div>
        <AgainButton action={view.action} onGo={onGoMeasure} onAgain={(port) => measure.runUsb(antenna.id, port)} />
      </div>
    </section>
  )
}

type AgainProps = { action: BarAction; onGo: () => void; onAgain: (port: string) => void }

/** `again`: same port as the last USB measurement and the range boxes as they are now. */
function AgainButton({ action, onGo, onAgain }: AgainProps) {
  const press = () => (action.type === 'again' ? onAgain(action.port) : onGo())
  return (
    <div className="next-measure-action">
      <button
        type="button"
        className={action.type === 'go' ? 'button-secondary' : undefined}
        disabled={action.disabled}
        onClick={press}
      >
        {action.label}
      </button>
      <small>{action.text}</small>
    </div>
  )
}

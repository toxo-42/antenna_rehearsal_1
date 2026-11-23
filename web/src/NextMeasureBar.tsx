import { ErrorNotice } from './Badges.tsx'
import { ChangeNoteFields } from './ChangeNoteFields.tsx'
import { LengthField } from './LengthField.tsx'
import type { Antenna } from './types.ts'
import { rangeText } from './usbRange.ts'
import type { MeasureState } from './useAppState.ts'

interface BarProps {
  antenna: Antenna
  measure: MeasureState
  onGoMeasure: () => void
}

/**
 * Under the verdict: note what was changed and measure again without leaving the screen.
 * Nothing is measured until the student presses the button.
 */
export function NextMeasureBar({ antenna, measure, onGoMeasure }: BarProps) {
  return (
    <section className="card next-measure" aria-label="다음 측정">
      {measure.error !== null && <ErrorNotice error={measure.error} />}
      {measure.busy && (
        <p className="notice" role="status">
          측정하는 중…
        </p>
      )}
      <div className="next-measure-row">
        <div>
          <h2>다음 측정</h2>
          <small>고친 내용을 적고 다시 측정합니다</small>
        </div>
        {antenna.kind === 'monopole' && <LengthField measure={measure} />}
        <ChangeNoteFields measure={measure} />
        <AgainButton antenna={antenna} measure={measure} onGoMeasure={onGoMeasure} />
      </div>
    </section>
  )
}

/** Same port as the last USB measurement and the range boxes as they are now. */
function AgainButton({ antenna, measure, onGoMeasure }: BarProps) {
  const port = measure.lastPort
  if (port === null) {
    return (
      <div className="next-measure-action">
        <button type="button" className="button-secondary" disabled={measure.busy} onClick={onGoMeasure}>
          측정 화면으로 →
        </button>
        <small>VNA로 한 번 측정하면 여기서 바로 다시 측정할 수 있습니다</small>
      </div>
    )
  }
  return (
    <div className="next-measure-action">
      <button type="button" disabled={measure.busy} onClick={() => measure.runUsb(antenna.id, port)}>
        같은 설정으로 다시 측정
      </button>
      <small>VNA (USB) · {rangeText(measure.usbRange)}</small>
    </div>
  )
}

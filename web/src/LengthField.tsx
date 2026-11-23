import { lengthNotice } from './lengthInput.ts'
import type { MeasureState } from './useAppState.ts'

/**
 * The conductor length right now (monopole only, optional). With it the verdict looks for the
 * resonance where that length should resonate; left empty, it works from the target alone.
 */
export function LengthField({ measure }: { measure: MeasureState }) {
  const notice = lengthNotice(measure.length)
  return (
    <div className="field-stack">
      <label className="field field-short">
        지금 도체 길이 (cm)
        <input
          type="text"
          inputMode="decimal"
          value={measure.length}
          placeholder="예: 12"
          disabled={measure.busy}
          onChange={(event) => measure.setLength(event.target.value)}
        />
      </label>
      {notice !== null && <p className="explain-warning">{notice}</p>}
    </div>
  )
}

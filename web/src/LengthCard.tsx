import { lengthNotice } from './lengthInput.ts'
import type { MeasureState } from './useAppState.ts'

/**
 * The conductor length right now (monopole only, optional). With it the verdict looks for the
 * resonance where that length should resonate; left empty, it works from the target alone.
 */
export function LengthCard({ measure }: { measure: MeasureState }) {
  const notice = lengthNotice(measure.length)
  return (
    <section className="card">
      <h2>2-나. 지금 도체 길이 (선택)</h2>
      <label className="field">
        안테나 도체 길이 (cm)
        <input
          type="text"
          inputMode="decimal"
          value={measure.length}
          placeholder="예: 12"
          onChange={(event) => measure.setLength(event.target.value)}
        />
      </label>
      {notice !== null && <p className="explain-warning">{notice}</p>}
      <p className="muted">
        급전점에서 도체 끝까지 잰 길이입니다. 자르거나 덧붙였으면 고쳐 주세요. 비워 두면 목표 주파수만으로
        판정합니다.
      </p>
    </section>
  )
}

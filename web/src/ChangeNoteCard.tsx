import { ACTIONS, AMOUNTS, NO_CHANGE, PARTS, UNITS } from './changeNote.ts'
import type { NoteChoice } from './changeNote.ts'
import type { MeasureState } from './useAppState.ts'

const FIELDS: { key: keyof NoteChoice; label: string; options: readonly string[] }[] = [
  { key: 'part', label: '부품', options: PARTS },
  { key: 'action', label: '동작', options: ACTIONS },
  { key: 'amount', label: '수치', options: AMOUNTS },
  { key: 'unit', label: '단위', options: UNITS },
]

/** What was changed since the last measurement. Picked from lists, so nothing is guessed. */
export function ChangeNoteCard({ measure }: { measure: MeasureState }) {
  const { note, setNote } = measure
  const noPart = note.part === NO_CHANGE
  return (
    <section className="card">
      <h2>2-가. 지난 측정 뒤 바꾼 것</h2>
      <div className="field-row">
        {FIELDS.map((field) => (
          <label key={field.key} className="field">
            {field.label}
            <select
              value={note[field.key]}
              disabled={measure.busy || (field.key !== 'part' && noPart)}
              onChange={(event) => setNote({ ...note, [field.key]: event.target.value })}
            >
              {field.options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      <p className="muted">
        저장될 기록: <strong>{measure.changeNote === '' ? '없음' : measure.changeNote}</strong>
      </p>
    </section>
  )
}

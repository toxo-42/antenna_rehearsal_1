import { ACTIONS, NO_CHANGE, PARTS, UNITS, amountNotice } from './changeNote.ts'
import type { NoteChoice } from './changeNote.ts'
import type { MeasureState } from './useAppState.ts'

type ListKey = 'part' | 'action' | 'unit'

interface PickProps {
  measure: MeasureState
  name: ListKey
  label: string
  options: readonly string[]
}

/** What was changed since the last measurement: three lists and a typed amount, no free text. */
export function ChangeNoteFields({ measure }: { measure: MeasureState }) {
  const { note, setNote } = measure
  const notice = amountNotice(note.amount)
  return (
    <div className="field-stack">
      <div className="field-grid">
        <Pick measure={measure} name="part" label="부품" options={PARTS} />
        <Pick measure={measure} name="action" label="동작" options={ACTIONS} />
        <label className="field">
          수치
          <input
            type="text"
            inputMode="decimal"
            value={note.amount}
            placeholder="예: 5"
            disabled={measure.busy || note.part === NO_CHANGE}
            onChange={(event) => setNote({ ...note, amount: event.target.value })}
          />
        </label>
        <Pick measure={measure} name="unit" label="단위" options={UNITS} />
      </div>
      {notice !== null && <p className="explain-warning">{notice}</p>}
    </div>
  )
}

function Pick({ measure, name, label, options }: PickProps) {
  const { note, setNote } = measure
  const change = (value: string): NoteChoice => ({ ...note, [name]: value })
  return (
    <label className="field">
      {label}
      <select
        value={note[name]}
        disabled={measure.busy || (name !== 'part' && note.part === NO_CHANGE)}
        onChange={(event) => setNote(change(event.target.value))}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

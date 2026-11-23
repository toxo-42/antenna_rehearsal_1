// What the student typed for the next measurement of one antenna, and the error of its last
// failed one. All of it belongs to that antenna: another antenna starts empty. Pure functions.

import type { ErrorInfo } from './api.ts'
import { EMPTY_NOTE } from './changeNote.ts'
import type { NoteChoice } from './changeNote.ts'

export interface Draft {
  antennaId: number | null
  /** The conductor length as typed. It stays for the next measurement of the same antenna. */
  length: string
  note: NoteChoice
  error: ErrorInfo | null
}

export function emptyDraft(antennaId: number | null): Draft {
  return { antennaId, length: '', note: EMPTY_NOTE, error: null }
}

/** The same draft while the antenna is the same; an empty one once another antenna is chosen. */
export function draftFor(draft: Draft, antennaId: number | null): Draft {
  return draft.antennaId === antennaId ? draft : emptyDraft(antennaId)
}

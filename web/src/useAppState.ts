import { useCallback, useState } from 'react'
import { describeError, listAntennas, measureUsb } from './api.ts'
import type { ErrorInfo, MeasureNotes } from './api.ts'
import { lengthToSend } from './lengthInput.ts'
import { EMPTY_NOTE, changeNoteText } from './changeNote.ts'
import type { NoteChoice } from './changeNote.ts'
import { DEFAULT_CAL_MODE } from './labels.ts'
import { latestOnly } from './latest.ts'
import { chosenAntennaId, shownAntennas } from './manage.ts'
import { draftFor, emptyDraft } from './measureDraft.ts'
import type { Draft } from './measureDraft.ts'
import { DEFAULT_METHOD } from './measureMethod.ts'
import type { Method } from './measureMethod.ts'
import type { Antenna, CalMode, Measurement } from './types.ts'
import { DEFAULT_USB_RANGE, rangeNotice } from './usbRange.ts'
import type { RangeBoxes } from './usbRange.ts'
import { useLoad } from './useLoad.ts'

/**
 * The stored antennas and which one is chosen. After an add, a rename or a delete the list is
 * loaded again (`refresh`) and replaces the old one whole: nothing from this session is kept on
 * top of it. The old list stays on screen until the new one arrives, so the screen never blinks.
 */
export function useAntennas() {
  const [loaded, loadFirst] = useLoad(() => listAntennas(), 'antennas')
  const [fresh, setFresh] = useState<Antenna[] | null>(null)
  const [chosenId, setChosenId] = useState<number | null>(null)
  const [latest] = useState(latestOnly)
  const reload = useCallback(() => {
    latest.next() // a refresh still on its way is dropped
    setFresh(null)
    loadFirst()
  }, [latest, loadFirst])
  const refresh = useCallback(async () => {
    const ticket = latest.next()
    try {
      const list = await listAntennas()
      if (latest.isCurrent(ticket)) setFresh(list)
    } catch {
      if (latest.isCurrent(ticket)) reload() // shows the error with its "retry" button
    }
  }, [latest, reload])
  const antennas = shownAntennas(fresh, loaded.status === 'ready' ? loaded.data : [])
  const antennaId = chosenAntennaId(antennas, chosenId)
  return { loaded, reload, refresh, antennas, antennaId, select: setChosenId }
}

export type MeasureState = ReturnType<typeof useMeasure>

/**
 * Calibration choice and the running measurement. Kept above the tabs so the choice survives
 * a tab change; the tabs are locked while a measurement runs, so its answer is never lost.
 * `antenna` is the chosen one: the typed length, the note and the error belong to it.
 */
export function useMeasure(onMeasured: (measurement: Measurement) => void, antenna: Antenna | null) {
  const [calMode, setCalMode] = useState<CalMode>(DEFAULT_CAL_MODE)
  const draft = useDraft(antenna?.id ?? null)
  const source = useSource()
  const [busy, setBusy] = useState(false)

  async function run(measure: () => Promise<Measurement>) {
    setBusy(true)
    draft.setError(null)
    try {
      onMeasured(await measure())
      draft.setNote(EMPTY_NOTE) // a note belongs to one measurement; the next one starts empty
    } catch (failure) {
      draft.setError(describeError(failure))
    } finally {
      setBusy(false)
    }
  }
  const changeNote = changeNoteText(draft.note)
  const notes: MeasureNotes = { changeNote, lengthCm: lengthToSend(draft.length, antenna?.kind ?? null) }
  /** One USB measurement with the range boxes as they are now; the port is kept for "again". */
  const runUsb = async (antennaId: number, port: string) => {
    if (rangeNotice(source.usbRange) !== null) return // boxes that cannot be sent: nothing is sent
    await run(async () => {
      const measured = await measureUsb(antennaId, { port, ...source.usbRange }, calMode, notes)
      source.setLastPort(port)
      return measured
    })
  }
  const clearError = () => draft.setError(null)
  return { calMode, setCalMode, ...draft, ...source, changeNote, notes, busy, run, runUsb, clearError }
}

/**
 * The length, the change note and the last error of the chosen antenna. Choosing another antenna
 * empties all three (see measureDraft.ts); within one antenna the length stays for the next
 * measurement, because the student edits it only after trimming the conductor.
 */
function useDraft(antennaId: number | null) {
  const [stored, setDraft] = useState<Draft>(() => emptyDraft(antennaId))
  const draft = draftFor(stored, antennaId)
  if (draft !== stored) setDraft(draft)
  const patch = (change: Partial<Draft>) => setDraft((previous) => ({ ...previous, ...change }))
  return {
    note: draft.note,
    length: draft.length,
    error: draft.error,
    setNote: (note: NoteChoice) => patch({ note }),
    setLength: (length: string) => patch({ length }),
    setError: (error: ErrorInfo | null) => patch({ error }),
  }
}

/** Where the sweep comes from. Kept above the tabs so the choices survive a tab change. */
function useSource() {
  // The card's "fill this range" button reaches these boxes from another tab.
  const [usbRange, setUsbRange] = useState<RangeBoxes>(DEFAULT_USB_RANGE)
  // The port of the last USB measurement that worked: "measure again" on the card uses it.
  const [lastPort, setLastPort] = useState<string | null>(null)
  const [method, setMethod] = useState<Method>(DEFAULT_METHOD)
  // Synthetic samples join the methods only once practice is asked for.
  const [practice, setPractice] = useState(false)
  const startPractice = () => {
    setPractice(true)
    setMethod('sample')
  }
  return { usbRange, setUsbRange, lastPort, setLastPort, method, setMethod, practice, startPractice }
}

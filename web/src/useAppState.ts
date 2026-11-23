import { useCallback, useState } from 'react'
import { describeError, listAntennas } from './api.ts'
import type { ErrorInfo, MeasureNotes } from './api.ts'
import { lengthValue } from './lengthInput.ts'
import { EMPTY_NOTE, changeNoteText } from './changeNote.ts'
import type { NoteChoice } from './changeNote.ts'
import { DEFAULT_CAL_MODE } from './labels.ts'
import type { Antenna, CalMode, Measurement } from './types.ts'
import { DEFAULT_USB_RANGE } from './usbRange.ts'
import type { RangeBoxes } from './usbRange.ts'
import { useLoad } from './useLoad.ts'

/** The stored antennas plus the ones added in this session, and which one is chosen. */
export function useAntennas() {
  const [loaded, reload] = useLoad(() => listAntennas(), 'antennas')
  const [added, setAdded] = useState<Antenna[]>([])
  const [chosenId, setChosenId] = useState<number | null>(null)
  const stored = loaded.status === 'ready' ? loaded.data : []
  const antennas = [...stored, ...added.filter((a) => !stored.some((s) => s.id === a.id))]
  const antennaId = chosenId ?? antennas[0]?.id ?? null

  const add = useCallback((antenna: Antenna) => {
    setAdded((previous) => [...previous, antenna])
    setChosenId(antenna.id)
  }, [])
  return { loaded, reload, antennas, antennaId, select: setChosenId, add }
}

export type MeasureState = ReturnType<typeof useMeasure>

/**
 * Calibration choice and the running measurement. Kept above the tabs so the choice survives
 * a tab change; the tabs are locked while a measurement runs, so its answer is never lost.
 */
export function useMeasure(onMeasured: (measurement: Measurement) => void) {
  const [calMode, setCalMode] = useState<CalMode>(DEFAULT_CAL_MODE)
  const [note, setNote] = useState<NoteChoice>(EMPTY_NOTE)
  // Kept here so the card's "fill this range" button can reach the USB boxes on another tab.
  const [usbRange, setUsbRange] = useState<RangeBoxes>(DEFAULT_USB_RANGE)
  // The conductor length as typed. Unlike the note it stays for the next measurement: the
  // student edits it only after trimming the conductor.
  const [length, setLength] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ErrorInfo | null>(null)

  async function run(measure: () => Promise<Measurement>) {
    setBusy(true)
    setError(null)
    try {
      onMeasured(await measure())
      setNote(EMPTY_NOTE) // a note belongs to one measurement; the next one starts empty
    } catch (failure) {
      setError(describeError(failure))
    } finally {
      setBusy(false)
    }
  }
  const changeNote = changeNoteText(note)
  const notes: MeasureNotes = { changeNote, lengthCm: lengthValue(length) }
  const boxes = { note, setNote, length, setLength, usbRange, setUsbRange }
  return { calMode, setCalMode, ...boxes, changeNote, notes, busy, error, run }
}

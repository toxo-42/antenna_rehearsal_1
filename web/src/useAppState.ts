import { useCallback, useState } from 'react'
import { describeError, listAntennas } from './api.ts'
import type { ErrorInfo } from './api.ts'
import { DEFAULT_CAL_MODE } from './labels.ts'
import type { Antenna, CalMode, Measurement } from './types.ts'
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
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ErrorInfo | null>(null)

  async function run(measure: () => Promise<Measurement>) {
    setBusy(true)
    setError(null)
    try {
      onMeasured(await measure())
    } catch (failure) {
      setError(describeError(failure))
    } finally {
      setBusy(false)
    }
  }
  return { calMode, setCalMode, busy, error, run }
}

// The manage screen: the questions asked before a delete, and which antenna stays chosen after
// one. Pure functions.

import { timeText } from './labels.ts'
import type { Antenna, Source } from './types.ts'

/** The source of an overview row's latest measurement; none when the field is missing. */
export function lastSource(row: { last_source?: Source | null }): Source | null {
  return row.last_source ?? null
}

/**
 * The antennas to show: the list loaded after the last add, rename or delete, otherwise the one
 * loaded first. Nothing is kept on top of it, so a reused id never hides or renames a row.
 */
export function shownAntennas(fresh: Antenna[] | null, stored: Antenna[]): Antenna[] {
  return fresh ?? stored
}

const NO_UNDO = '삭제하면 되돌릴 수 없습니다.'

/** Asked before deleting an antenna: its name and how many measurements go with it. */
export function antennaDeleteQuestion(name: string, measurementCount: number): string {
  const what = measurementCount > 0 ? `"${name}" 안테나와 측정 ${measurementCount}건을 모두` : `"${name}" 안테나를`
  return `${what} 삭제할까요? ${NO_UNDO}`
}

/** Asked before deleting one measurement. */
export function measurementDeleteQuestion(measuredAt: string): string {
  return `${timeText(measuredAt)} 측정을 삭제할까요? ${NO_UNDO}`
}

/** The chosen antenna while it still exists, otherwise the first one left (null when none). */
export function chosenAntennaId(antennas: readonly { id: number }[], chosenId: number | null): number | null {
  if (chosenId !== null && antennas.some((antenna) => antenna.id === chosenId)) return chosenId
  return antennas[0]?.id ?? null
}

// The manage screen: the questions asked before a delete, and which antenna stays chosen after
// one. Pure functions.

import { timeText } from './labels.ts'

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

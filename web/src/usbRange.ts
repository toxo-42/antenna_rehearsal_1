/** SAA-2 USB measurement: range rule and the notices shown next to the measure button. */

import type { Remeasure } from './types.ts'

/** What the three range boxes hold. */
export interface RangeBoxes {
  startMhz: number
  stopMhz: number
  points: number
}

export const DEFAULT_USB_RANGE: RangeBoxes = { startMhz: 2000, stopMhz: 3000, points: 201 }

/** Fill the range boxes with the card's suggestion. The point count stays; nothing is measured. */
export function withRemeasure(boxes: RangeBoxes, remeasure: Remeasure): RangeBoxes {
  return { ...boxes, startMhz: remeasure.start_mhz, stopMhz: remeasure.stop_mhz }
}

export const START_FRACTION = 0.5
export const STOP_FRACTION = 1.5

export const USB_MODE_NOTICE =
  '측정을 누르면 SAA-2 화면이 "USB MODE"로 바뀌고 장비 조작이 멈춥니다. 다시 쓰려면 전원을 껐다 켜 주세요.'

export const USB_CAL_NOTICE =
  'USB로 받은 값에는 장비의 교정이 반영되지 않습니다. 위 교정 상태와 관계없이 unknown(교정 안 됨)으로 저장됩니다.'

/**
 * The port to measure with: the chosen one while it is still listed, otherwise the first listed
 * (SAA-2 comes first). A port that vanished on refresh is never sent.
 */
export function choosePort(chosen: string | null, ports: string[] | null): string | null {
  if (ports === null) return null
  if (chosen !== null && ports.includes(chosen)) return chosen
  return ports[0] ?? null
}

/**
 * Warn when the range ends below 1.5x the target or starts above 0.5x the target. A resonance
 * near the edge of the range can measure under 3 dB deep and be missed. Never blocks measuring.
 */
export function rangeWarning(startMhz: number, stopMhz: number, targetMhz: number | null): string | null {
  if (targetMhz === null || !Number.isFinite(startMhz) || !Number.isFinite(stopMhz)) return null
  if (stopMhz >= targetMhz * STOP_FRACTION && startMhz <= targetMhz * START_FRACTION) return null
  const low = targetMhz * START_FRACTION
  const high = targetMhz * STOP_FRACTION
  return (
    `범위가 목표 ${targetMhz} MHz에 비해 좁습니다 (권장: ${low} MHz 이하에서 ${high} MHz 이상). ` +
    '공진이 범위 끝에 가까우면 깊이가 3 dB 미만으로 계산되어 놓칠 수 있습니다.'
  )
}

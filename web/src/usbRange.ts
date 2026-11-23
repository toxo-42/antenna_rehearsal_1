/** SAA-2 USB measurement: range rule and the notices shown next to the measure button. */

import { calModeLabel } from './labels.ts'
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

/** "216~650 MHz · 201점": the range the measure-again button will use. */
export function rangeText(boxes: RangeBoxes): string {
  return `${boxes.startMhz}~${boxes.stopMhz} MHz · ${boxes.points}점`
}

export const MIN_POINTS = 11
export const MAX_POINTS = 1001
export const RANGE_NOTICE = '측정 범위를 숫자로 입력해 주세요'
export const POINTS_NOTICE = `점 개수는 ${MIN_POINTS}~${MAX_POINTS} 사이의 정수로 입력해 주세요`

/** True when the boxes hold numbers: start and stop finite, the point count an integer. */
export function rangeUsable(boxes: RangeBoxes): boolean {
  return Number.isFinite(boxes.startMhz) && Number.isFinite(boxes.stopMhz) && Number.isInteger(boxes.points)
}

/**
 * Why the boxes cannot be sent, or null when they can. An emptied box asks for numbers; a point
 * count that is a number but not an integer from 11 to 1001 gets its own sentence.
 */
export function rangeNotice(boxes: RangeBoxes): string | null {
  const { startMhz, stopMhz, points } = boxes
  if (![startMhz, stopMhz, points].every(Number.isFinite)) return RANGE_NOTICE
  if (!rangeUsable(boxes) || points < MIN_POINTS || points > MAX_POINTS) return POINTS_NOTICE
  return null
}

/** "216.55": at most two decimals, no trailing zeros. */
function mhzText(mhz: number): string {
  return String(Number(mhz.toFixed(2)))
}

export const START_FRACTION = 0.5
export const STOP_FRACTION = 1.5

export const USB_MODE_NOTICE =
  '측정을 누르면 VNA 화면이 "USB MODE"로 바뀌고 장비 조작이 멈춥니다. 다시 쓰려면 전원을 껐다 켜 주세요.'

export const USB_CAL_NOTICE =
  `USB로 받은 값에는 VNA의 교정이 반영되지 않습니다. 위 Calibration 선택과 관계없이 "${calModeLabel('unknown')}"으로 저장됩니다.`

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
  const low = mhzText(targetMhz * START_FRACTION)
  const high = mhzText(targetMhz * STOP_FRACTION)
  return (
    `범위가 목표 ${mhzText(targetMhz)} MHz에 비해 좁습니다 (권장: ${low} MHz 이하에서 ${high} MHz 이상). ` +
    '공진이 범위 끝에 가까우면 깊이가 3 dB 미만으로 계산되어 놓칠 수 있습니다.'
  )
}

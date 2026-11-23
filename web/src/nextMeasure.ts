// What the "다음 측정" bar under the verdict shows. Pure function; NextMeasureBar only draws it.

import { savedNoteText } from './changeNote.ts'
import type { Kind } from './types.ts'
import { rangeNotice, rangeText } from './usbRange.ts'
import type { RangeBoxes } from './usbRange.ts'

export interface BarInput {
  kind: Kind
  /** The port of the last USB measurement that worked; null before the first one. */
  lastPort: string | null
  boxes: RangeBoxes
  busy: boolean
  changeNote: string
}

/** `go`: open the measure screen. `again`: measure on `port` with the range boxes as they are. */
export type BarAction =
  | { type: 'go'; label: string; text: string; disabled: boolean }
  | { type: 'again'; port: string; label: string; text: string; disabled: boolean }

export interface BarView {
  /** The conductor length box: a monopole only. */
  showLength: boolean
  savedText: string
  action: BarAction
}

const GO_LABEL = '측정 화면으로 →'
const GO_HINT = 'VNA로 한 번 측정하면 여기서 바로 다시 측정할 수 있습니다'
const AGAIN_LABEL = '같은 설정으로 다시 측정'

function barAction({ lastPort, boxes, busy }: BarInput): BarAction {
  if (lastPort === null) return { type: 'go', label: GO_LABEL, text: GO_HINT, disabled: busy }
  const notice = rangeNotice(boxes)
  return {
    type: 'again',
    port: lastPort,
    label: AGAIN_LABEL,
    // Boxes that cannot be sent show why instead of a range like "NaN~3000 MHz".
    text: notice ?? `VNA (USB) · ${rangeText(boxes)}`,
    disabled: busy || notice !== null,
  }
}

export function nextMeasureView(input: BarInput): BarView {
  return {
    showLength: input.kind === 'monopole',
    savedText: savedNoteText(input.changeNote),
    action: barAction(input),
  }
}

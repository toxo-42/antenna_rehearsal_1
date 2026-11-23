import assert from 'node:assert/strict'
import { test } from 'node:test'
import { nextMeasureView } from './nextMeasure.ts'
import type { BarInput } from './nextMeasure.ts'
import { POINTS_NOTICE, RANGE_NOTICE } from './usbRange.ts'

const base: BarInput = {
  kind: 'monopole',
  lastPort: null,
  boxes: { startMhz: 216, stopMhz: 650, points: 201 },
  busy: false,
  changeNote: '',
}

test('before a USB measurement worked: a hint and the way to the measure screen', () => {
  assert.deepEqual(nextMeasureView(base).action, {
    type: 'go',
    label: '측정 화면으로 →',
    text: 'VNA로 한 번 측정하면 여기서 바로 다시 측정할 수 있습니다',
    disabled: false,
  })
})

test('after a USB measurement worked: measure again on that port with the range as text', () => {
  assert.deepEqual(nextMeasureView({ ...base, lastPort: '/dev/cu.usbmodem4001' }).action, {
    type: 'again',
    port: '/dev/cu.usbmodem4001',
    label: '같은 설정으로 다시 측정',
    text: 'VNA (USB) · 216~650 MHz · 201점',
    disabled: false,
  })
})

test('the length field is for a monopole only', () => {
  assert.equal(nextMeasureView(base).showLength, true)
  assert.equal(nextMeasureView({ ...base, kind: 'patch' }).showLength, false)
  assert.equal(nextMeasureView({ ...base, kind: 'patch', lastPort: 'COM3' }).showLength, false)
})

test('range boxes that hold no number: the notice replaces the range and the button is off', () => {
  const boxes = { startMhz: Number.NaN, stopMhz: 3000, points: 201 }
  const action = nextMeasureView({ ...base, lastPort: 'COM3', boxes }).action
  assert.equal(action.type, 'again')
  assert.equal(action.text, RANGE_NOTICE)
  assert.equal(action.disabled, true)
  assert.doesNotMatch(action.text, /NaN/)
})

test('a point count outside 11~1001: its notice replaces the range and the button is off', () => {
  const action = nextMeasureView({ ...base, lastPort: 'COM3', boxes: { ...base.boxes, points: 5 } }).action
  assert.equal(action.text, POINTS_NOTICE)
  assert.equal(action.disabled, true)
})

test('unusable boxes do not block the way to the measure screen, where they are fixed', () => {
  const boxes = { startMhz: Number.NaN, stopMhz: 3000, points: 201 }
  assert.equal(nextMeasureView({ ...base, boxes }).action.disabled, false)
})

test('both buttons are off while a measurement runs', () => {
  assert.equal(nextMeasureView({ ...base, busy: true }).action.disabled, true)
  assert.equal(nextMeasureView({ ...base, busy: true, lastPort: 'COM3' }).action.disabled, true)
})

test('the bar previews the note that will be stored, like the measure screen', () => {
  assert.equal(nextMeasureView(base).savedText, '저장될 기록: 없음')
  assert.equal(nextMeasureView({ ...base, changeNote: '도체 줄임 5 mm' }).savedText, '저장될 기록: 도체 줄임 5 mm')
})

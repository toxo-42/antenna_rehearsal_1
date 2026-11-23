import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  DEFAULT_USB_RANGE,
  POINTS_NOTICE,
  RANGE_NOTICE,
  choosePort,
  rangeNotice,
  rangeText,
  rangeUsable,
  rangeWarning,
  withRemeasure,
} from './usbRange.ts'

test('the suggested range replaces start and stop and keeps the point count', () => {
  const filled = withRemeasure({ startMhz: 10, stopMhz: 3000, points: 401 }, { start_mhz: 498, stop_mhz: 748, note: '' })

  assert.deepEqual(filled, { startMhz: 498, stopMhz: 748, points: 401 })
  assert.equal(DEFAULT_USB_RANGE.points, 201)
})

test('a chosen port that is still listed stays chosen', () => {
  assert.equal(choosePort('/dev/b', ['/dev/a', '/dev/b']), '/dev/b')
})

test('without a choice the first port (SAA-2 first) is used', () => {
  assert.equal(choosePort(null, ['/dev/a', '/dev/b']), '/dev/a')
})

test('a chosen port that disappeared after a refresh falls back to the first one', () => {
  assert.equal(choosePort('/dev/gone', ['/dev/a']), '/dev/a')
})

test('no ports means nothing to measure with, even with an old choice', () => {
  assert.equal(choosePort('/dev/gone', []), null)
  assert.equal(choosePort(null, null), null)
})

test('a range from half to one and a half times the target has no warning', () => {
  assert.equal(rangeWarning(1225, 3675, 2450), null)
  assert.equal(rangeWarning(100, 1000, 433), null)
})

test('a stop below 1.5 times the target warns', () => {
  assert.match(rangeWarning(100, 649, 433) ?? '', /3 dB/)
})

test('a start above half the target warns', () => {
  assert.match(rangeWarning(217, 1000, 433) ?? '', /3 dB/)
})

test('the spec example 2000~3000 MHz for a 2450 MHz patch warns', () => {
  assert.notEqual(rangeWarning(2000, 3000, 2450), null)
})

test('the range reads as one short line next to the measure-again button', () => {
  assert.equal(rangeText({ startMhz: 216, stopMhz: 650, points: 201 }), '216~650 MHz · 201점')
  assert.equal(rangeText({ startMhz: 0.05, stopMhz: 3000, points: 1001 }), '0.05~3000 MHz · 1001점')
})

test('missing numbers give no warning', () => {
  assert.equal(rangeWarning(Number.NaN, 3000, 2450), null)
  assert.equal(rangeWarning(2000, 3000, null), null)
})

test('the warning shows at most two decimals and no trailing zeros', () => {
  const decimal = rangeWarning(300, 500, 433.1) ?? ''
  assert.match(decimal, /목표 433\.1 MHz/)
  assert.match(decimal, /권장: 216\.55 MHz 이하에서 649\.65 MHz 이상/)
  assert.doesNotMatch(decimal, /\d\.\d{3}/)
  const whole = rangeWarning(2000, 3000, 2450) ?? ''
  assert.match(whole, /권장: 1225 MHz 이하에서 3675 MHz 이상/)
  assert.match(rangeWarning(300, 500, 433.333) ?? '', /216\.67 MHz 이하에서 650 MHz 이상/)
})

test('range boxes are usable when start and stop are numbers and the point count is an integer', () => {
  assert.equal(rangeUsable(DEFAULT_USB_RANGE), true)
  assert.equal(rangeUsable({ startMhz: 0.05, stopMhz: 3000, points: 11 }), true)
  assert.equal(rangeUsable({ startMhz: Number.NaN, stopMhz: 3000, points: 201 }), false)
  assert.equal(rangeUsable({ startMhz: 2000, stopMhz: Number.NaN, points: 201 }), false)
  assert.equal(rangeUsable({ startMhz: 2000, stopMhz: Number.POSITIVE_INFINITY, points: 201 }), false)
  assert.equal(rangeUsable({ startMhz: 2000, stopMhz: 3000, points: Number.NaN }), false)
  assert.equal(rangeUsable({ startMhz: 2000, stopMhz: 3000, points: 200.5 }), false)
})

test('an emptied range box asks for numbers', () => {
  assert.equal(RANGE_NOTICE, '측정 범위를 숫자로 입력해 주세요')
  assert.equal(rangeNotice(DEFAULT_USB_RANGE), null)
  assert.equal(rangeNotice({ startMhz: Number.NaN, stopMhz: 3000, points: 201 }), RANGE_NOTICE)
  assert.equal(rangeNotice({ startMhz: 2000, stopMhz: Number.NaN, points: 201 }), RANGE_NOTICE)
  assert.equal(rangeNotice({ startMhz: 2000, stopMhz: 3000, points: Number.NaN }), RANGE_NOTICE)
})

test('a point count that is not an integer from 11 to 1001 is explained in Korean', () => {
  assert.equal(POINTS_NOTICE, '점 개수는 11~1001 사이의 정수로 입력해 주세요')
  for (const points of [10, 1002, 0, -201, 200.5]) {
    assert.equal(rangeNotice({ startMhz: 2000, stopMhz: 3000, points }), POINTS_NOTICE, String(points))
  }
  assert.equal(rangeNotice({ startMhz: 2000, stopMhz: 3000, points: 11 }), null)
  assert.equal(rangeNotice({ startMhz: 2000, stopMhz: 3000, points: 1001 }), null)
})

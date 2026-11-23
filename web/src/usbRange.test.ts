import assert from 'node:assert/strict'
import { test } from 'node:test'
import { DEFAULT_USB_RANGE, choosePort, rangeText, rangeWarning, withRemeasure } from './usbRange.ts'

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

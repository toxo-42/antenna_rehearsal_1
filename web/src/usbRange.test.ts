import assert from 'node:assert/strict'
import { test } from 'node:test'
import { choosePort, rangeWarning } from './usbRange.ts'

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

test('missing numbers give no warning', () => {
  assert.equal(rangeWarning(Number.NaN, 3000, 2450), null)
  assert.equal(rangeWarning(2000, 3000, null), null)
})

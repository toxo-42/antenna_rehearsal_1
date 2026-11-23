import assert from 'node:assert/strict'
import { test } from 'node:test'
import { methodLabel, visibleMethods } from './measureMethod.ts'

test('the measure screen offers the VNA and a CSV file; the VNA comes first', () => {
  assert.deepEqual(visibleMethods(false), ['usb', 'csv'])
})

test('synthetic samples appear only after practice is asked for', () => {
  assert.deepEqual(visibleMethods(true), ['usb', 'csv', 'sample'])
})

test('method labels use the words of the screen, and the sample one says it is synthetic', () => {
  assert.equal(methodLabel('usb'), 'VNA (USB)')
  assert.equal(methodLabel('csv'), 'CSV 파일')
  assert.match(methodLabel('sample'), /합성/)
})

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { HISTORY_LIMIT } from './api.ts'
import { antennaSummary, countText } from './summary.ts'
import type { MeasurementRow } from './types.ts'

function row(id: number, patch: Partial<MeasurementRow> = {}): MeasurementRow {
  return {
    id,
    antenna_id: 1,
    measured_at: '2026-11-23T10:00:00',
    source: 'usb',
    cal_mode: 'unknown',
    stage: 'good',
    resonance_mhz: 433,
    s11_db: -20,
    bandwidth_pct: 5,
    change_note: '',
    length_cm: null,
    ...patch,
  }
}

test('no measurements: count 0 and no latest values', () => {
  assert.deepEqual(antennaSummary([]), { count: 0, latestStage: null, latestResonanceMhz: null, latestSource: null })
})

test('the first row is the newest, so the summary takes its stage and resonance', () => {
  const rows = [row(3, { stage: 'offtarget', resonance_mhz: 412.5 }), row(2), row(1)]
  assert.deepEqual(antennaSummary(rows), { count: 3, latestStage: 'offtarget', latestResonanceMhz: 412.5, latestSource: 'usb' })
})

test('a newest measurement without a resonance keeps null instead of an older value', () => {
  const rows = [row(2, { stage: 'none', resonance_mhz: null }), row(1)]
  assert.deepEqual(antennaSummary(rows), { count: 2, latestStage: 'none', latestResonanceMhz: null, latestSource: 'usb' })
})

test('count text: a full page says "or more" because older rows may be missing', () => {
  assert.equal(countText(0), '0회')
  assert.equal(countText(6), '6회')
  assert.equal(countText(HISTORY_LIMIT - 1), `${HISTORY_LIMIT - 1}회`)
  assert.equal(countText(HISTORY_LIMIT), `${HISTORY_LIMIT}회 이상`)
})

test('the summary carries the source of the newest row, so synthetic data keeps its badge', () => {
  const rows = [row(2, { source: 'synthetic' }), row(1, { source: 'usb' })]
  assert.equal(antennaSummary(rows).latestSource, 'synthetic')
  assert.equal(antennaSummary([row(1, { source: 'csv' })]).latestSource, 'csv')
})

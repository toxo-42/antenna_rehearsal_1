import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { PlotBox } from './chart.ts'
import { HISTORY_LIMIT } from './api.ts'
import { inMeasurementOrder, isTruncated, orderText, trendModel } from './trend.ts'
import type { MeasurementRow } from './types.ts'

const BOX: PlotBox = { left: 0, top: 0, width: 300, height: 100 }

function rowOf(id: number, measured_at: string, resonance_mhz: number | null): MeasurementRow {
  return {
    id, antenna_id: 1, measured_at, source: 'synthetic', cal_mode: 'vna', stage: 'good',
    resonance_mhz, s11_db: null, bandwidth_pct: null, change_note: '', length_cm: null,
  }
}

test('rows come back oldest first, ties broken by id', () => {
  const rows = [rowOf(3, '2026-01-02T00:00:00', 1), rowOf(2, '2026-01-01T00:00:00', 1), rowOf(1, '2026-01-02T00:00:00', 1)]
  assert.deepEqual(inMeasurementOrder(rows).map((row) => row.id), [2, 1, 3])
})

test('each measurement gets its place in order; one without resonance has no point', () => {
  const rows = [rowOf(2, '2026-01-02T00:00:00', 430), rowOf(1, '2026-01-01T00:00:00', 380), rowOf(3, '2026-01-03T00:00:00', null)]
  const model = trendModel(rows, 433, BOX)
  assert.deepEqual(model.points.map((p) => p.id), [1, 2])
  assert.deepEqual(model.points.map((p) => p.order), [1, 2])
  assert.equal(model.count, 3)
  assert.equal(model.points[0].x, 0)
  assert.equal(model.points[1].x, 150)
})

test('each point keeps its source, so synthetic data can be marked as such', () => {
  const rows = [rowOf(1, '2026-01-01T00:00:00', 380), { ...rowOf(2, '2026-01-02T00:00:00', 430), source: 'usb' as const }]
  const model = trendModel(rows, 433, BOX)
  assert.deepEqual(model.points.map((p) => p.source), ['synthetic', 'usb'])
  assert.equal(model.hasSynthetic, true)
  assert.equal(trendModel([rows[1]], 433, BOX).hasSynthetic, false)
})

test('an order is only "Nth" when the whole history is loaded', () => {
  assert.equal(orderText(1, false), '1번째')
  assert.equal(orderText(1, true), `최근 ${HISTORY_LIMIT}건 중 1번째`)
})

test('the history is cut when a full page came back', () => {
  assert.equal(isTruncated(HISTORY_LIMIT - 1), false)
  assert.equal(isTruncated(HISTORY_LIMIT), true)
})

test('the frequency axis always holds the target line', () => {
  const model = trendModel([rowOf(1, '2026-01-01T00:00:00', 380), rowOf(2, '2026-01-02T00:00:00', 390)], 433, BOX)
  assert.ok(model.targetY >= 0 && model.targetY <= 100)
  assert.ok(model.fMax >= 433)
  assert.ok(model.points[0].y > model.targetY) // lower frequency is drawn lower
})

test('a single measurement and no resonance at all still give a drawable model', () => {
  const single = trendModel([rowOf(1, '2026-01-01T00:00:00', 433)], 433, BOX)
  assert.equal(single.points[0].x, 150)
  assert.ok(Number.isFinite(single.points[0].y))
  const none = trendModel([rowOf(1, '2026-01-01T00:00:00', null)], 433, BOX)
  assert.deepEqual(none.points, [])
  assert.ok(Number.isFinite(none.targetY))
})

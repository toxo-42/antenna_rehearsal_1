import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  MATCH_LINE_DB,
  chartModel,
  chartScale,
  dbBottom,
  dbTicks,
  freqTicks,
  markerPoint,
  sweepPoints,
  xOf,
  yOf,
} from './chart.ts'
import type { ChartInput, PlotBox } from './chart.ts'
import type { SweepPoint } from './types.ts'

const BOX: PlotBox = { left: 50, top: 10, width: 400, height: 300 }

function sweepOf(...db: number[]): SweepPoint[] {
  return db.map((s11_db, i) => ({ f_mhz: 100 + i * 100, s11_db }))
}

test('the bottom of the dB axis is never shallower than -30', () => {
  assert.equal(dbBottom(sweepOf(-1, -25, -2)), -30)
  assert.equal(dbBottom(sweepOf(-1, -30, -2)), -30)
  assert.equal(dbBottom(sweepOf(-1, -30.5, -2)), -30.5)
})

test('the bottom of the dB axis is never deeper than -60', () => {
  assert.equal(dbBottom(sweepOf(-1, -45, -2)), -45)
  assert.equal(dbBottom(sweepOf(-1, -60, -2)), -60)
  assert.equal(dbBottom(sweepOf(-1, -60.5, -2)), -60)
  assert.equal(dbBottom(sweepOf(-1, -900, -2)), -60)
})

test('an empty sweep and a positive-only sweep still get the -30 bottom', () => {
  assert.equal(dbBottom([]), -30)
  assert.equal(dbBottom(sweepOf(0.4, 0.4)), -30)
})

test('both ends of the frequency axis land on the plot edges', () => {
  const scale = chartScale(sweepOf(-1, -20, -1), BOX)
  assert.equal(scale.fMin, 100)
  assert.equal(scale.fMax, 300)
  assert.equal(xOf(100, scale), 50)
  assert.equal(xOf(300, scale), 450)
  assert.equal(xOf(200, scale), 250)
})

test('0 dB is the top of the plot and the axis bottom is the bottom', () => {
  const scale = chartScale(sweepOf(-1, -40, -1), BOX)
  assert.equal(scale.dbBottom, -40)
  assert.equal(yOf(0, scale), 10)
  assert.equal(yOf(-40, scale), 310)
  assert.equal(yOf(-20, scale), 160)
})

test('values outside the dB range stick to the axis ends', () => {
  const scale = chartScale(sweepOf(-1, -80, 0.4), BOX)
  assert.equal(scale.dbBottom, -60)
  assert.equal(yOf(-80, scale), 310)
  assert.equal(yOf(0.4, scale), 10)
  const points = sweepPoints(sweepOf(-1, -80, 0.4), scale)
  assert.deepEqual(points[1], { x: 250, y: 310 })
  assert.deepEqual(points[2], { x: 450, y: 10 })
})

test('frequencies outside the sweep stick to the plot edges', () => {
  const scale = chartScale(sweepOf(-1, -20, -1), BOX)
  assert.equal(xOf(5, scale), 50)
  assert.equal(xOf(5000, scale), 450)
})

test('a sweep with one point does not throw and gives finite coordinates', () => {
  const sweep: SweepPoint[] = [{ f_mhz: 10, s11_db: -0.01 }]
  const scale = chartScale(sweep, BOX)
  const points = sweepPoints(sweep, scale)
  assert.equal(points.length, 1)
  assert.ok(Number.isFinite(points[0].x) && Number.isFinite(points[0].y))
  assert.ok(points[0].x >= 50 && points[0].x <= 450)
  assert.ok(Number.isFinite(xOf(433, scale)))
})

test('an empty sweep does not throw', () => {
  const scale = chartScale([], BOX)
  assert.deepEqual(sweepPoints([], scale), [])
  assert.ok(Number.isFinite(xOf(433, scale)))
  assert.ok(Number.isFinite(yOf(-10, scale)))
})

test('the marker uses the response values, not the minimum of the sweep', () => {
  const sweep = sweepOf(-1, -20, -50)
  const scale = chartScale(sweep, BOX)
  assert.deepEqual(markerPoint(200, -20, scale), { x: 250, y: yOf(-20, scale) })
})

test('no marker when the response has no resonance', () => {
  const scale = chartScale(sweepOf(-1, -20, -1), BOX)
  assert.equal(markerPoint(null, null, scale), null)
  assert.equal(markerPoint(200, null, scale), null)
  assert.equal(markerPoint(null, -20, scale), null)
})

test('a sweep with 200,000 points (a 2 MB CSV) does not throw', () => {
  const sweep = Array.from({ length: 200_000 }, (_, i) => ({ f_mhz: 10 + i * 0.005, s11_db: -1 }))
  const scale = chartScale(sweep, BOX)
  assert.equal(scale.fMin, 10)
  assert.equal(scale.fMax, 10 + 199_999 * 0.005)
  assert.equal(chartModel({ ...inputOf(sweep), antenna: { target_mhz: 433 } }, BOX).curve.length, 200_000)
})

test('dB ticks run every 10 dB from 0 down to the axis bottom', () => {
  assert.deepEqual(dbTicks(chartScale(sweepOf(-1, -40, -1), BOX)), [0, -10, -20, -30, -40])
  assert.deepEqual(dbTicks(chartScale(sweepOf(-1, -5, -1), BOX)), [0, -10, -20, -30])
  assert.deepEqual(dbTicks(chartScale(sweepOf(-1, -35, -1), BOX)), [0, -10, -20, -30])
})

test('frequency ticks are five even steps over the sweep, one for a single point', () => {
  assert.deepEqual(freqTicks(chartScale(sweepOf(-1, -2, -1), BOX)), [100, 150, 200, 250, 300])
  assert.deepEqual(freqTicks(chartScale([{ f_mhz: 10, s11_db: -1 }], BOX)), [10])
})

function inputOf(sweep: SweepPoint[]): ChartInput {
  return { sweep, antenna: { target_mhz: 200 }, resonance_mhz: null, s11_db: null }
}

test('frequency tick labels are whole MHz on a wide sweep', () => {
  const sweep = [{ f_mhz: 10, s11_db: -1 }, { f_mhz: 1000, s11_db: -1 }]
  const labels = chartModel(inputOf(sweep), BOX).freqTicks.map((tick) => tick.label)
  assert.deepEqual(labels, ['10', '258', '505', '753', '1000'])
})

test('frequency tick labels stay distinct on a narrow sweep', () => {
  const sweep = [{ f_mhz: 433.1, s11_db: -1 }, { f_mhz: 433.4, s11_db: -1 }]
  const labels = chartModel(inputOf(sweep), BOX).freqTicks.map((tick) => tick.label)
  assert.equal(new Set(labels).size, 5, labels.join(' '))
  assert.equal(labels[0], '433.10')
  assert.equal(labels[4], '433.40')
})

test('the match line is at -10 dB', () => {
  assert.equal(MATCH_LINE_DB, -10)
  const model = chartModel(inputOf(sweepOf(-1, -40, -1)), BOX)
  assert.equal(model.matchY, yOf(-10, model.scale))
})

test('the target line is drawn at the antenna target, not at the resonance', () => {
  const input = { ...inputOf(sweepOf(-1, -20, -1)), resonance_mhz: 200, s11_db: -20 }
  const model = chartModel({ ...input, antenna: { target_mhz: 250 } }, BOX)
  assert.equal(model.targetX, xOf(250, model.scale))
  assert.notEqual(model.targetX, model.marker?.x)
})

test('the model marker comes from the response, not from the sweep minimum', () => {
  const input = { ...inputOf(sweepOf(-1, -12, -50)), resonance_mhz: 200, s11_db: -12 }
  const model = chartModel(input, BOX)
  assert.deepEqual(model.marker, { x: 250, y: yOf(-12, model.scale) })
  assert.equal(chartModel(inputOf(sweepOf(-1, -12, -50)), BOX).marker, null)
})

test('the model curve has one point per sweep point', () => {
  const model = chartModel(inputOf(sweepOf(-1, -20, -1)), BOX)
  assert.deepEqual(model.curve, sweepPoints(sweepOf(-1, -20, -1), model.scale))
})

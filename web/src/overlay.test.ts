import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { PlotBox } from './chart.ts'
import { overlayModel } from './overlay.ts'
import type { SweepPoint } from './types.ts'

const BOX: PlotBox = { left: 0, top: 0, width: 100, height: 100 }

function sweep(from: number, to: number, db: number): SweepPoint[] {
  return [{ f_mhz: from, s11_db: 0 }, { f_mhz: (from + to) / 2, s11_db: db }, { f_mhz: to, s11_db: 0 }]
}

test('both sweeps share one scale that covers both of them', () => {
  const model = overlayModel(sweep(100, 300, -20), sweep(200, 500, -45), 433, BOX)
  assert.equal(model.scale.fMin, 100)
  assert.equal(model.scale.fMax, 500)
  assert.equal(model.scale.dbBottom, -45)
  assert.equal(model.before[0].x, 0)
  assert.equal(model.after[2].x, 100)
})

test('frequency ticks keep enough decimals to stay distinct on a narrow sweep', () => {
  const model = overlayModel(sweep(433.0, 433.4, -20), sweep(433.0, 433.4, -20), 433.2, BOX)
  const labels = model.freqTicks.map((tick) => tick.label)
  assert.equal(new Set(labels).size, labels.length)
  assert.equal(labels[0], '433.00')
  assert.equal(model.freqTicks[0].x, 0)
  assert.equal(model.freqTicks[labels.length - 1].x, 100)
})

test('the target line sits on the shared scale', () => {
  const model = overlayModel(sweep(100, 300, -20), sweep(200, 500, -20), 300, BOX)
  assert.equal(model.targetX, 50)
})

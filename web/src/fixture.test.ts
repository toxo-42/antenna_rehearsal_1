import assert from 'node:assert/strict'
import { test } from 'node:test'
import raw from './fixtures/measurement.json' with { type: 'json' }
import { CAL_MODES, KINDS, SOURCES, STAGES } from './types.ts'
import type { Measurement } from './types.ts'

// JSON imports type every string as `string`, so the value-list fields are widened here and
// checked at run time below. Everything else (keys, nesting, number/string/array) is checked
// by the build: this assignment stops compiling when the fixture and types.ts disagree.
type Widen<T> = T extends string
  ? string
  : T extends (infer Item)[]
    ? Widen<Item>[]
    : T extends object
      ? { [Key in keyof T]: Widen<T[Key]> }
      : T

const fixture: Widen<Measurement> = raw

function includes(values: readonly string[], value: string): boolean {
  return values.includes(value)
}

test('the fixture uses only values from the value lists', () => {
  assert.ok(includes(STAGES, fixture.card.stage))
  assert.ok(includes(SOURCES, fixture.source))
  assert.ok(includes(KINDS, fixture.antenna.kind))
  assert.ok(includes(CAL_MODES, fixture.cal_mode))
})

test('the fixture has no key that types.ts does not know', () => {
  const known: Record<keyof Measurement, true> = {
    id: true,
    antenna: true,
    source: true,
    cal_mode: true,
    measured_at: true,
    change_note: true,
    resonance_mhz: true,
    s11_db: true,
    bandwidth_pct: true,
    sweep: true,
    card: true,
  }
  assert.deepEqual(Object.keys(fixture).sort(), Object.keys(known).sort())
})

test('the fixture sweep is long enough to draw', () => {
  assert.ok(fixture.sweep.length > 100)
})

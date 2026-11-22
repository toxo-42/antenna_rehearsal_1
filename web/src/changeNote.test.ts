import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ACTIONS, AMOUNTS, NO_CHANGE, PARTS, UNITS, changeNoteText } from './changeNote.ts'

test('the choices are the fixed lists of the spec', () => {
  assert.deepEqual(PARTS, ['없음', '도체', '접지판', '케이블', '교정', '납땜'])
  assert.deepEqual(ACTIONS, ['없음', '줄임', '늘림', '변경'])
  assert.ok(AMOUNTS.includes(NO_CHANGE))
  assert.ok(UNITS.length > 0)
})

test('part, action, amount and unit become one note', () => {
  assert.equal(changeNoteText({ part: '도체', action: '줄임', amount: '5', unit: 'mm' }), '도체 줄임 5 mm')
})

test('no part means no note at all', () => {
  assert.equal(changeNoteText({ part: '없음', action: '줄임', amount: '5', unit: 'mm' }), '')
})

test('no action and no amount are left out', () => {
  assert.equal(changeNoteText({ part: '교정', action: '없음', amount: '없음', unit: 'mm' }), '교정')
  assert.equal(changeNoteText({ part: '케이블', action: '변경', amount: '없음', unit: 'cm' }), '케이블 변경')
})

import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ACTIONS, EMPTY_NOTE, PARTS, UNITS, amountNotice, amountValue, changeNoteText, savedNoteText } from './changeNote.ts'

test('the choices are the fixed lists of the spec', () => {
  assert.deepEqual(PARTS, ['없음', '도체', '접지판', '케이블', '교정', '납땜'])
  assert.deepEqual(ACTIONS, ['없음', '줄임', '늘림', '변경'])
  assert.ok(UNITS.length > 0)
})

test('part, action, amount and unit become one note', () => {
  assert.equal(changeNoteText({ part: '도체', action: '줄임', amount: '5', unit: 'mm' }), '도체 줄임 5 mm')
})

test('the amount is typed: any plain positive number is kept as typed, without spaces', () => {
  assert.equal(changeNoteText({ part: '도체', action: '줄임', amount: ' 8 ', unit: 'mm' }), '도체 줄임 8 mm')
  assert.equal(changeNoteText({ part: '도체', action: '줄임', amount: '0.5', unit: 'cm' }), '도체 줄임 0.5 cm')
  assert.equal(amountValue('8.25'), '8.25')
  assert.equal(amountValue('1234'), '1234')
})

test('no part means no note at all', () => {
  assert.equal(changeNoteText({ part: '없음', action: '줄임', amount: '5', unit: 'mm' }), '')
  assert.equal(changeNoteText(EMPTY_NOTE), '')
})

test('no action and an empty amount are left out', () => {
  assert.equal(changeNoteText({ part: '교정', action: '없음', amount: '', unit: 'mm' }), '교정')
  assert.equal(changeNoteText({ part: '케이블', action: '변경', amount: '  ', unit: 'cm' }), '케이블 변경')
})

test('an amount that is not a plain positive number is left out of the note and explained', () => {
  for (const typed of ['0', '0.0', '-5', '05', '5.125', '12345', '1e3', '조금', '5 mm']) {
    assert.equal(amountValue(typed), null, typed)
    assert.equal(changeNoteText({ part: '도체', action: '줄임', amount: typed, unit: 'mm' }), '도체 줄임', typed)
    assert.equal(amountNotice(typed), '0보다 큰 숫자만 입력해 주세요 (예: 5 또는 0.5, 소수 둘째 자리까지).', typed)
  }
})

test('an empty or valid amount needs no notice', () => {
  assert.equal(amountNotice(''), null)
  assert.equal(amountNotice('  '), null)
  assert.equal(amountNotice('5'), null)
})

test('the preview says what will be stored, and "없음" for an empty note', () => {
  assert.equal(savedNoteText(''), '저장될 기록: 없음')
  assert.equal(savedNoteText('도체 줄임 5 mm'), '저장될 기록: 도체 줄임 5 mm')
})

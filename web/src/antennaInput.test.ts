import assert from 'node:assert/strict'
import { test } from 'node:test'
import { NAME_NOTICE, TARGET_NOTICE, antennaInputError, targetValue } from './antennaInput.ts'

test('a name and a positive target are sent', () => {
  assert.equal(antennaInputError('모노폴 B', '433'), null)
  assert.equal(antennaInputError('패치', ' 2450.5 '), null)
  assert.equal(targetValue(' 2450.5 '), 2450.5)
})

test('a blank name is refused in Korean before anything is sent', () => {
  assert.equal(NAME_NOTICE, '안테나 이름을 입력해 주세요')
  assert.equal(antennaInputError('', '433'), NAME_NOTICE)
  assert.equal(antennaInputError('   ', '433'), NAME_NOTICE)
})

test('an empty, non-numeric, zero, negative or infinite target is refused in Korean', () => {
  assert.equal(TARGET_NOTICE, '목표 주파수를 숫자로 입력해 주세요 (MHz)')
  for (const typed of ['', '  ', '433MHz', 'abc', '0', '-433', 'Infinity', 'NaN']) {
    assert.equal(antennaInputError('모노폴 B', typed), TARGET_NOTICE, typed)
  }
})

test('no notice holds an English identifier', () => {
  assert.doesNotMatch(`${NAME_NOTICE}${TARGET_NOTICE}`.replace('MHz', ''), /[A-Za-z_]/)
})

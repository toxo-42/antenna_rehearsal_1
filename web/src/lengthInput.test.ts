import assert from 'node:assert/strict'
import { test } from 'node:test'
import { lengthNotice, lengthToSend, lengthValue } from './lengthInput.ts'

test('an empty box means the length was not entered', () => {
  assert.equal(lengthValue(''), null)
  assert.equal(lengthValue('   '), null)
  assert.equal(lengthNotice(''), null)
})

test('a number is sent as it is, and the server checks its range', () => {
  assert.equal(lengthValue('12'), 12)
  assert.equal(lengthValue(' 11.5 '), 11.5)
  assert.equal(lengthValue('0'), 0)
  assert.equal(lengthNotice('11.5'), null)
})

test('text that is not a number is not sent, and the screen only asks for a number', () => {
  assert.equal(lengthValue('12cm'), null)
  assert.equal(lengthValue('Infinity'), null)
  assert.equal(lengthNotice('12cm'), '숫자만 입력해 주세요 (예: 12 또는 11.5).')
})

test('the length is sent for a monopole only: a patch has no length box, so nothing is sent', () => {
  assert.equal(lengthToSend('16.4', 'monopole'), 16.4)
  assert.equal(lengthToSend('', 'monopole'), null)
  assert.equal(lengthToSend('16.4', 'patch'), null)
  assert.equal(lengthToSend('16.4', null), null)
})

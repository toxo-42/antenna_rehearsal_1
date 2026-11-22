import assert from 'node:assert/strict'
import { test } from 'node:test'
import { latestOnly } from './latest.ts'

test('only the newest ticket is current', () => {
  const latest = latestOnly()
  const first = latest.next()
  assert.equal(latest.isCurrent(first), true)
  const second = latest.next()
  assert.equal(latest.isCurrent(first), false)
  assert.equal(latest.isCurrent(second), true)
})

test('a late answer for an older click is dropped (A clicked, then B, A answers last)', () => {
  const latest = latestOnly()
  const shown: string[] = []
  const ticketA = latest.next()
  const ticketB = latest.next()
  const answer = (ticket: number, value: string) => latest.isCurrent(ticket) && shown.push(value)
  answer(ticketB, 'B')
  answer(ticketA, 'A')
  assert.deepEqual(shown, ['B'])
})

test('separate trackers do not share tickets', () => {
  const one = latestOnly()
  const two = latestOnly()
  const ticket = one.next()
  two.next()
  two.next()
  assert.equal(one.isCurrent(ticket), true)
})

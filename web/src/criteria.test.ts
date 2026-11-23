import assert from 'node:assert/strict'
import { test } from 'node:test'
import { listCriteria } from './api.ts'
import { criteriaByTone } from './criteria.ts'
import type { Criterion } from './types.ts'

const ITEMS: Criterion[] = [
  { stage: 'good', text: 'g' },
  { stage: 'narrow', text: 'n' },
  { stage: 'offtarget', text: 'o' },
  { stage: 'unmatched', text: 'u' },
  { stage: 'none', text: 'x' },
  { stage: 'invalid', text: 'i' },
]

test('criteria are grouped under the three states of the chip, good first', () => {
  const groups = criteriaByTone(ITEMS)
  assert.deepEqual(groups.map((group) => group.tone), ['good', 'caution', 'problem'])
  assert.deepEqual(groups.map((group) => group.label), ['양호', '주의', '문제'])
  assert.deepEqual(groups.map((group) => group.texts), [['g'], ['n', 'o'], ['u', 'x', 'i']])
})

test('each group carries its symbol, so color is never the only cue', () => {
  const symbols = criteriaByTone(ITEMS).map((group) => group.symbol)
  assert.equal(new Set(symbols).size, 3)
})

test('the server sentences are shown as they are, and a state without one is left out', () => {
  const groups = criteriaByTone([{ stage: 'none', text: '목표 근처에 공진이 없습니다.' }])
  assert.deepEqual(groups, [{ tone: 'problem', label: '문제', symbol: '×', texts: ['목표 근처에 공진이 없습니다.'] }])
})

test('the criteria are read for the kind of the antenna', async () => {
  const paths: string[] = []
  const fetchFn = (async (path: string) => {
    paths.push(path)
    return new Response('[]', { status: 200 })
  }) as typeof fetch
  assert.deepEqual(await listCriteria('patch', fetchFn), [])
  assert.deepEqual(paths, ['/api/criteria?kind=patch'])
})

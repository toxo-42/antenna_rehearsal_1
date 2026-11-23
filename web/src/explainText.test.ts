import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  ASK_NOT_IN_CARD,
  EXPLAIN_BUTTON,
  EXPLAIN_LABEL,
  askNotice,
  explainNotice,
  explanationBlocks,
  warningText,
} from './explainText.ts'

test('only ## headings and numbered lists become formatting', () => {
  const text = [
    '## 한 줄 결론',
    '공진은 있지만 **목표**에 맞지 않습니다.',
    '## 지금 해 볼 것',
    '1. 도체를 줄입니다.',
    '2) 다시 잽니다.',
    '- 점 목록은 글 그대로',
    '### 작은 제목도 글 그대로',
  ].join('\n')

  assert.deepEqual(explanationBlocks(text), [
    { kind: 'heading', text: '한 줄 결론' },
    { kind: 'paragraph', text: '공진은 있지만 **목표**에 맞지 않습니다.' },
    { kind: 'heading', text: '지금 해 볼 것' },
    { kind: 'list', start: 1, items: ['도체를 줄입니다.', '다시 잽니다.'] },
    { kind: 'paragraph', text: '- 점 목록은 글 그대로' },
    { kind: 'paragraph', text: '### 작은 제목도 글 그대로' },
  ])
})

test('a list keeps its first number, and blank lines split lists', () => {
  assert.deepEqual(explanationBlocks('3. 셋\n\n4. 넷\n\n'), [
    { kind: 'list', start: 3, items: ['셋'] },
    { kind: 'list', start: 4, items: ['넷'] },
  ])
})

test('the label says the card is the authority', () => {
  assert.equal(EXPLAIN_BUTTON, 'AI 튜터에게 설명 듣기')
  assert.equal(EXPLAIN_LABEL, 'AI 설명(참고용). 결론과 수치는 위 카드가 기준입니다')
})

test('warnings list the numbers the card does not have', () => {
  assert.equal(warningText([]), null)
  assert.equal(warningText(['50', '44']), '카드에 없는 수치가 있습니다: 50, 44')
})

test('a rejected or failed explanation shows only a notice', () => {
  assert.equal(explainNotice('rejected'), 'AI 설명이 카드와 달라 표시하지 않습니다')
  assert.match(explainNotice('failed') ?? '', /만들지 못했습니다/)
  assert.equal(explainNotice('ok'), null)
  assert.equal(explainNotice('off'), null)
})

test('a linked guide outside the card says so', () => {
  assert.equal(ASK_NOT_IN_CARD, '이번 측정에서는 나타나지 않은 항목입니다')
  assert.equal(askNotice('none'), '관련 설명 없음')
  assert.match(askNotice('failed') ?? '', /직접 골라/)
  assert.equal(askNotice('matched'), null)
})

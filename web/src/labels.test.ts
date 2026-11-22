import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  DEFAULT_CAL_MODE,
  calModeLabel,
  kindLabel,
  sourceLabel,
  sourceSymbol,
  stageLabel,
  stageSymbol,
  stageTone,
} from './labels.ts'
import { CAL_MODES, KINDS, SOURCES, STAGES } from './types.ts'

test('stage decides the tone: good, caution, problem', () => {
  assert.equal(stageTone('good'), 'good')
  assert.equal(stageTone('narrow'), 'caution')
  assert.equal(stageTone('offtarget'), 'caution')
  assert.equal(stageTone('unmatched'), 'problem')
  assert.equal(stageTone('none'), 'problem')
  assert.equal(stageTone('invalid'), 'problem')
})

test('the six stage values are all covered', () => {
  assert.equal(STAGES.length, 6)
  for (const stage of STAGES) {
    assert.ok(['good', 'caution', 'problem'].includes(stageTone(stage)), stage)
  }
})

test('stage label is the tone in Korean, and invalid reads as a measurement error', () => {
  assert.equal(stageLabel('good'), '양호')
  assert.equal(stageLabel('narrow'), '주의')
  assert.equal(stageLabel('offtarget'), '주의')
  assert.equal(stageLabel('unmatched'), '문제')
  assert.equal(stageLabel('none'), '문제')
  assert.equal(stageLabel('invalid'), '측정 오류')
})

test('each tone has its own symbol, so color is never the only cue', () => {
  const symbols = new Set([stageSymbol('good'), stageSymbol('narrow'), stageSymbol('none')])
  assert.equal(symbols.size, 3)
  assert.equal(stageSymbol('offtarget'), stageSymbol('narrow'))
  assert.equal(stageSymbol('invalid'), stageSymbol('unmatched'))
  for (const stage of STAGES) assert.notEqual(stageSymbol(stage).trim(), '', stage)
})

test('source decides the badge text', () => {
  assert.equal(SOURCES.length, 4)
  assert.equal(sourceLabel('usb'), '실측')
  assert.equal(sourceLabel('csv'), 'CSV')
  assert.equal(sourceLabel('synthetic'), '합성 데이터')
  assert.equal(sourceLabel('stored'), '저장된 측정')
})

test('a stored measurement is never labelled as a live measurement', () => {
  assert.ok(!sourceLabel('stored').includes('실측'))
  assert.ok(!sourceLabel('synthetic').includes('실측'))
})

test('kind and calibration values have Korean labels', () => {
  assert.equal(kindLabel('monopole'), '모노폴')
  assert.equal(kindLabel('patch'), '패치')
  assert.equal(calModeLabel('vna'), '본체에서 교정함')
  assert.equal(calModeLabel('unknown'), '확인되지 않음')
  assert.equal(KINDS.length, 2)
  assert.equal(CAL_MODES.length, 2)
})

test('the state symbols are ○ good, △ caution, × problem', () => {
  assert.equal(stageSymbol('good'), '○')
  assert.equal(stageSymbol('narrow'), '△')
  assert.equal(stageSymbol('offtarget'), '△')
  assert.equal(stageSymbol('unmatched'), '×')
  assert.equal(stageSymbol('none'), '×')
  assert.equal(stageSymbol('invalid'), '×')
})

test('each source badge has its own symbol', () => {
  assert.equal(sourceSymbol('usb'), '●')
  assert.equal(sourceSymbol('csv'), '▤')
  assert.equal(sourceSymbol('synthetic'), '◇')
  assert.equal(sourceSymbol('stored'), '▣')
})

test('calibration starts as "not confirmed" so the student has to choose', () => {
  assert.equal(DEFAULT_CAL_MODE, 'unknown')
})

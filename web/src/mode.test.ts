import assert from 'node:assert/strict'
import { test } from 'node:test'
import { isDemo, screenFor, shownTab, visibleTabs } from './mode.ts'

const TABS = [{ id: 'measure' }, { id: 'card' }, { id: 'history' }] as const
const health = (mode: string) => ({ mode, ollama: false, explain: false, ports: [] })

test('demo mode comes only from a health answer that says demo', () => {
  assert.equal(isDemo(health('demo')), true)
  assert.equal(isDemo(health('local')), false)
  assert.equal(isDemo(null), false)
})

test('demo mode hides the measure tab and keeps the others in order', () => {
  assert.deepEqual(visibleTabs(TABS, true).map((tab) => tab.id), ['card', 'history'])
  assert.deepEqual(visibleTabs(TABS, false).map((tab) => tab.id), ['measure', 'card', 'history'])
})

test('demo mode starts on the history tab instead of the hidden measure tab', () => {
  assert.equal(shownTab('measure', true), 'history')
  assert.equal(shownTab('card', true), 'card')
  assert.equal(shownTab('measure', false), 'measure')
})

test('demo screen: badge, no measure tab, starts on history', () => {
  const screen = screenFor(TABS, 'measure', health('demo'))
  assert.equal(screen.badge, '시연 모드')
  assert.deepEqual(screen.tabs.map((tab) => tab.id), ['card', 'history'])
  assert.equal(screen.tab, 'history')
})

test('local screen, and a screen whose mode is not known, stay as before', () => {
  for (const known of [health('local'), null]) {
    const screen = screenFor(TABS, 'measure', known)
    assert.equal(screen.badge, null)
    assert.deepEqual(screen.tabs.map((tab) => tab.id), ['measure', 'card', 'history'])
    assert.equal(screen.tab, 'measure')
  }
})

test('demo empty-state texts never send the student to the hidden measure tab', () => {
  const demo = Object.values(screenFor(TABS, 'card', health('demo')).empty)
  const local = Object.values(screenFor(TABS, 'card', health('local')).empty)
  assert.equal(demo.length, 3)
  for (const text of demo) assert.doesNotMatch(text, /①|측정에서/)
  assert.ok(demo.some((text) => text.includes('③ 이력')))
  for (const text of local) assert.match(text, /① 측정에서/)
})

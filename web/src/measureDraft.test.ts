import assert from 'node:assert/strict'
import { test } from 'node:test'
import { EMPTY_NOTE } from './changeNote.ts'
import { draftFor, emptyDraft } from './measureDraft.ts'
import type { Draft } from './measureDraft.ts'

const typed: Draft = {
  antennaId: 1,
  length: '16.4',
  note: { part: '도체', action: '줄임', amount: '5', unit: 'mm' },
  error: { message: '측정하지 못했습니다.', serverDown: false },
}

test('within one antenna the length, the note and the error stay as they are', () => {
  assert.equal(draftFor(typed, 1), typed)
})

test('another antenna starts with no length, no note and no error', () => {
  assert.deepEqual(draftFor(typed, 2), { antennaId: 2, length: '', note: EMPTY_NOTE, error: null })
})

test('losing the antenna (deleted, none left) clears the draft too', () => {
  assert.deepEqual(draftFor(typed, null), emptyDraft(null))
})

test('going back to the first antenna does not bring its old draft back', () => {
  assert.deepEqual(draftFor(draftFor(typed, 2), 1), emptyDraft(1))
})

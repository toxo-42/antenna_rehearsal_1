import assert from 'node:assert/strict'
import { test } from 'node:test'
import { deleteAntenna, deleteMeasurement, getOverview, renameAntenna } from './api.ts'
import { antennaDeleteQuestion, chosenAntennaId, lastSource, measurementDeleteQuestion, shownAntennas } from './manage.ts'

type Sent = { path: string; init: RequestInit | undefined }

function recorder(body: string): { sent: Sent[]; fetchFn: typeof fetch } {
  const sent: Sent[] = []
  const fetchFn = (async (path: string, init?: RequestInit) => {
    sent.push({ path, init })
    return new Response(body, { status: 200 })
  }) as typeof fetch
  return { sent, fetchFn }
}

test('the overview is a plain read', async () => {
  const { sent, fetchFn } = recorder('[]')
  assert.deepEqual(await getOverview(fetchFn), [])
  assert.deepEqual(sent, [{ path: '/api/antennas/overview', init: undefined }])
})

test('rename sends only the name', async () => {
  const { sent, fetchFn } = recorder('{"id":3,"name":"새 이름","kind":"patch","target_mhz":2450}')
  const renamed = await renameAntenna(3, '새 이름', fetchFn)
  assert.equal(renamed.name, '새 이름')
  assert.equal(sent[0].path, '/api/antennas/3')
  assert.equal(sent[0].init?.method, 'PATCH')
  assert.deepEqual(JSON.parse(String(sent[0].init?.body)), { name: '새 이름' })
})

test('deletes use DELETE on the one antenna or measurement', async () => {
  const { sent, fetchFn } = recorder('{"deleted_measurements":2}')
  assert.deepEqual(await deleteAntenna(3, fetchFn), { deleted_measurements: 2 })
  await deleteMeasurement(7, fetchFn)
  assert.deepEqual(sent.map((item) => [item.path, item.init?.method]), [
    ['/api/antennas/3', 'DELETE'],
    ['/api/measurements/7', 'DELETE'],
  ])
})

test('the antenna question names it, counts what goes with it, and says it cannot be undone', () => {
  const text = antennaDeleteQuestion('모노폴 A', 6)
  assert.match(text, /모노폴 A/)
  assert.match(text, /측정 6건/)
  assert.match(text, /되돌릴 수 없습니다/)
  assert.doesNotMatch(antennaDeleteQuestion('모노폴 B', 0), /측정 0건/)
  assert.match(antennaDeleteQuestion('모노폴 B', 0), /되돌릴 수 없습니다/)
})

test('the measurement question names the time and says it cannot be undone', () => {
  const text = measurementDeleteQuestion('2026-11-23T10:58:39')
  assert.match(text, /2026-11-23 10:58:39/)
  assert.match(text, /되돌릴 수 없습니다/)
})

test('a chosen antenna that was deleted falls back to the first one left', () => {
  const antennas = [{ id: 2 }, { id: 5 }]
  assert.equal(chosenAntennaId(antennas, 5), 5)
  assert.equal(chosenAntennaId(antennas, 9), 2)
  assert.equal(chosenAntennaId(antennas, null), 2)
  assert.equal(chosenAntennaId([], 9), null)
})

test('the overview row gives the source of its latest measurement; a missing field is none', () => {
  assert.equal(lastSource({ last_source: 'synthetic' }), 'synthetic')
  assert.equal(lastSource({ last_source: 'usb' }), 'usb')
  assert.equal(lastSource({ last_source: null }), null)
  assert.equal(lastSource({}), null)
})

test('the list loaded after a change replaces the first one, also when an id is used again', () => {
  const first = [{ id: 1, name: '모노폴 A', kind: 'monopole', target_mhz: 433 } as const]
  // Antenna 1 was deleted and the server gave its id to the antenna added next.
  const fresh = [{ id: 1, name: '패치 B', kind: 'patch', target_mhz: 2450 } as const]
  assert.deepEqual(shownAntennas(fresh, first), fresh)
  assert.deepEqual(shownAntennas([], first), [])
  assert.deepEqual(shownAntennas(null, first), first)
})

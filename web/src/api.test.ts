import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  ApiError,
  HISTORY_LIMIT,
  SERVER_DOWN_MESSAGE,
  createAntenna,
  describeError,
  getMeasurement,
  listAntennas,
  listMeasurements,
  listSamples,
  measureSample,
  request,
  uploadCsv,
} from './api.ts'

function respond(status: number, body: string): typeof fetch {
  return async () => new Response(body, { status })
}

async function failure(fetchFn: typeof fetch): Promise<ApiError> {
  try {
    await request('/api/antennas', undefined, fetchFn)
  } catch (error) {
    assert.ok(error instanceof ApiError)
    return error
  }
  throw new Error('request did not fail')
}

test('a successful response is returned as parsed JSON', async () => {
  const data = await request('/api/antennas', undefined, respond(200, '[{"id": 1}]'))
  assert.deepEqual(data, [{ id: 1 }])
})

test('a 422 with detail shows the server sentence as it is', async () => {
  const detail = '목표 433 MHz가 측정 범위 500.00~1000.00 MHz 밖입니다. 다시 측정해 주세요.'
  const error = await failure(respond(422, JSON.stringify({ detail })))
  assert.equal(error.message, detail)
  assert.equal(error.serverDown, false)
})

test('a 404 with detail also shows the server sentence', async () => {
  const error = await failure(respond(404, '{"detail": "측정 7번이 없습니다."}'))
  assert.equal(error.message, '측정 7번이 없습니다.')
  assert.equal(error.serverDown, false)
})

test('a 5xx without detail means the server is down (dev proxy answer)', async () => {
  for (const body of ['', 'Internal Server Error', '{}', '{"detail": 3}']) {
    const error = await failure(respond(500, body))
    assert.equal(error.message, SERVER_DOWN_MESSAGE, body)
    assert.equal(error.serverDown, true)
  }
  assert.equal((await failure(respond(502, ''))).serverDown, true)
})

test('a 5xx with detail still shows the server sentence', async () => {
  const error = await failure(respond(500, '{"detail": "저장하지 못했습니다."}'))
  assert.equal(error.message, '저장하지 못했습니다.')
  assert.equal(error.serverDown, false)
})

test('a failed request means the server is down', async () => {
  const error = await failure(async () => {
    throw new TypeError('fetch failed')
  })
  assert.equal(error.message, SERVER_DOWN_MESSAGE)
  assert.equal(error.serverDown, true)
})

test('a 4xx without detail is an error but not a server-down one', async () => {
  const error = await failure(respond(400, 'nope'))
  assert.equal(error.serverDown, false)
  assert.ok(error.message.includes('400'))
})

test('the server-down message is Korean and tells the student what to do', () => {
  assert.match(SERVER_DOWN_MESSAGE, /서버/)
})

test('an empty detail counts as no detail', async () => {
  assert.equal((await failure(respond(500, '{"detail": ""}'))).serverDown, true)
  const error = await failure(respond(422, '{"detail": ""}'))
  assert.equal(error.serverDown, false)
  assert.ok(error.message.includes('422'))
})

test('a connection lost while reading the body means the server is down', async () => {
  const broken = { ok: true, status: 200, text: () => Promise.reject(new TypeError('terminated')) }
  const error = await failure(async () => broken as unknown as Response)
  assert.equal(error.message, SERVER_DOWN_MESSAGE)
  assert.equal(error.serverDown, true)
})

test('a 200 that is not JSON becomes a Korean API error', async () => {
  const error = await failure(respond(200, '<!doctype html><html></html>'))
  assert.equal(error.serverDown, false)
  assert.match(error.message, /응답/)
})

test('describeError keeps the server-down flag and wraps other errors', () => {
  assert.deepEqual(describeError(new ApiError(SERVER_DOWN_MESSAGE, true)), {
    message: SERVER_DOWN_MESSAGE,
    serverDown: true,
  })
  assert.deepEqual(describeError(new ApiError('측정 7번이 없습니다.', false)), {
    message: '측정 7번이 없습니다.',
    serverDown: false,
  })
  assert.equal(describeError(new Error('boom')).serverDown, false)
})

interface Sent {
  path: string
  init: RequestInit | undefined
}

function recorder(body = '{}'): { sent: Sent[]; fetchFn: typeof fetch } {
  const sent: Sent[] = []
  const fetchFn = async (input: RequestInfo | URL, init?: RequestInit) => {
    sent.push({ path: String(input), init })
    return new Response(body, { status: 200 })
  }
  return { sent, fetchFn }
}

test('reads go to the right paths, and history asks for the largest page', async () => {
  const { sent, fetchFn } = recorder('[]')
  await listAntennas(fetchFn)
  await listSamples(fetchFn)
  await listMeasurements(5, fetchFn)
  await getMeasurement(7, fetchFn)
  assert.equal(HISTORY_LIMIT, 200)
  assert.deepEqual(
    sent.map((item) => item.path),
    ['/api/antennas', '/api/samples', '/api/measurements?antenna_id=5&limit=200', '/api/measurements/7'],
  )
  assert.ok(sent.every((item) => item.init === undefined || item.init.method === undefined))
})

test('a synthetic measurement posts the exact body the API expects', async () => {
  const { sent, fetchFn } = recorder()
  await measureSample(3, 'open', 'unknown', fetchFn)
  assert.equal(sent[0].path, '/api/measurements')
  assert.equal(sent[0].init?.method, 'POST')
  assert.deepEqual(JSON.parse(String(sent[0].init?.body)), {
    antenna_id: 3,
    source: 'synthetic',
    sample: 'open',
    cal_mode: 'unknown',
  })
})

test('adding an antenna posts name, kind and target_mhz', async () => {
  const { sent, fetchFn } = recorder()
  await createAntenna({ name: '모노폴 B', kind: 'patch', target_mhz: 915 }, fetchFn)
  assert.equal(sent[0].path, '/api/antennas')
  assert.equal(sent[0].init?.method, 'POST')
  assert.deepEqual(JSON.parse(String(sent[0].init?.body)), {
    name: '모노폴 B',
    kind: 'patch',
    target_mhz: 915,
  })
})

test('a CSV upload sends the file, antenna_id and cal_mode as multipart', async () => {
  const { sent, fetchFn } = recorder()
  const file = new File(['f_mhz,s11_db\n'], 'sweep.csv', { type: 'text/csv' })
  await uploadCsv(4, file, 'vna', fetchFn)
  assert.equal(sent[0].path, '/api/measurements/upload')
  assert.equal(sent[0].init?.method, 'POST')
  const form = sent[0].init?.body
  assert.ok(form instanceof FormData)
  assert.equal((form.get('file') as File).name, 'sweep.csv')
  assert.equal(form.get('antenna_id'), '4')
  assert.equal(form.get('cal_mode'), 'vna')
})

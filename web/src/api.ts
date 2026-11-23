// Every API call lives here. Error responses are `{"detail": "한국어 문장"}` and that sentence is
// shown as it is. Paths are relative: the dev server proxies /api, the built app is same-origin.

import type {
  Antenna,
  AntennaInput,
  AntennaOverview,
  AskAnswer,
  CalMode,
  Comparison,
  Criterion,
  Explanation,
  GuideTopic,
  Health,
  Kind,
  Measurement,
  MeasurementRow,
  Sample,
} from './types.ts'

export const SERVER_DOWN_MESSAGE =
  '서버에 연결할 수 없습니다. 서버가 켜져 있는지 확인한 뒤 다시 시도해 주세요.'
export const BAD_RESPONSE_MESSAGE =
  '서버 응답을 읽을 수 없습니다. 앱 서버 주소가 맞는지 확인해 주세요.'

/** The largest page the API returns (`limit` maximum). */
export const HISTORY_LIMIT = 200

export class ApiError extends Error {
  /** True when the request never reached the app: it failed, or a proxy answered a bare 5xx. */
  readonly serverDown: boolean

  constructor(message: string, serverDown: boolean) {
    super(message)
    this.name = 'ApiError'
    this.serverDown = serverDown
  }
}

export interface ErrorInfo {
  message: string
  serverDown: boolean
}

/** What the screen shows for a failed call. API errors already carry the Korean sentence. */
export function describeError(error: unknown): ErrorInfo {
  if (error instanceof ApiError) return { message: error.message, serverDown: error.serverDown }
  return { message: String(error), serverDown: false }
}

function detailOf(text: string): string | null {
  try {
    const body: unknown = JSON.parse(text)
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      return typeof body.detail === 'string' && body.detail !== '' ? body.detail : null
    }
  } catch {
    // Not JSON (an empty or plain-text body): there is no detail to show.
  }
  return null
}

function errorFor(status: number, text: string): ApiError {
  const detail = detailOf(text)
  if (detail !== null) return new ApiError(detail, false)
  if (status >= 500) return new ApiError(SERVER_DOWN_MESSAGE, true)
  return new ApiError(`요청을 처리하지 못했습니다 (HTTP ${status}).`, false)
}

function parseBody<T>(text: string): T {
  try {
    return JSON.parse(text) as T
  } catch {
    throw new ApiError(BAD_RESPONSE_MESSAGE, false)
  }
}

/** Send one request and return the parsed JSON body. Throws `ApiError` for every failure. */
export async function request<T>(
  path: string,
  init?: RequestInit,
  fetchFn: typeof fetch = fetch,
): Promise<T> {
  let response: Response
  let text: string
  try {
    response = await fetchFn(path, init)
    text = await response.text() // the connection can also drop while the body arrives
  } catch {
    throw new ApiError(SERVER_DOWN_MESSAGE, true)
  }
  if (!response.ok) throw errorFor(response.status, text)
  return parseBody<T>(text)
}

function postJson(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export function listAntennas(fetchFn: typeof fetch = fetch): Promise<Antenna[]> {
  return request('/api/antennas', undefined, fetchFn)
}

export function createAntenna(input: AntennaInput, fetchFn: typeof fetch = fetch): Promise<Antenna> {
  return request('/api/antennas', postJson(input), fetchFn)
}

export function getOverview(fetchFn: typeof fetch = fetch): Promise<AntennaOverview[]> {
  return request('/api/antennas/overview', undefined, fetchFn)
}

export function renameAntenna(id: number, name: string, fetchFn: typeof fetch = fetch): Promise<Antenna> {
  const init = { ...postJson({ name }), method: 'PATCH' }
  return request(`/api/antennas/${id}`, init, fetchFn)
}

export function deleteAntenna(id: number, fetchFn: typeof fetch = fetch): Promise<{ deleted_measurements: number }> {
  return request(`/api/antennas/${id}`, { method: 'DELETE' }, fetchFn)
}

export function deleteMeasurement(id: number, fetchFn: typeof fetch = fetch): Promise<{ deleted: number }> {
  return request(`/api/measurements/${id}`, { method: 'DELETE' }, fetchFn)
}

export function listSamples(fetchFn: typeof fetch = fetch): Promise<Sample[]> {
  return request('/api/samples', undefined, fetchFn)
}

/** What the student wrote down for one measurement, sent with every source. */
export interface MeasureNotes {
  changeNote: string
  /** Conductor length now, in cm; null when not entered. */
  lengthCm: number | null
}

export function measureSample(
  antennaId: number,
  sample: string,
  calMode: CalMode,
  notes: MeasureNotes,
  fetchFn: typeof fetch = fetch,
): Promise<Measurement> {
  const body = {
    antenna_id: antennaId,
    source: 'synthetic',
    sample,
    cal_mode: calMode,
    change_note: notes.changeNote,
    length_cm: notes.lengthCm,
  }
  return request('/api/measurements', postJson(body), fetchFn)
}

export interface UsbRange {
  port: string
  startMhz: number
  stopMhz: number
  points: number
}

export function listPorts(fetchFn: typeof fetch = fetch): Promise<string[]> {
  return request('/api/ports', undefined, fetchFn)
}

export function measureUsb(
  antennaId: number,
  range: UsbRange,
  calMode: CalMode,
  notes: MeasureNotes,
  fetchFn: typeof fetch = fetch,
): Promise<Measurement> {
  const body = {
    antenna_id: antennaId,
    source: 'usb',
    port: range.port,
    start_mhz: range.startMhz,
    stop_mhz: range.stopMhz,
    points: range.points,
    cal_mode: calMode,
    change_note: notes.changeNote,
    length_cm: notes.lengthCm,
  }
  return request('/api/measurements', postJson(body), fetchFn)
}

export function uploadCsv(
  antennaId: number,
  file: File,
  calMode: CalMode,
  notes: MeasureNotes,
  fetchFn: typeof fetch = fetch,
): Promise<Measurement> {
  const form = new FormData()
  form.append('file', file)
  form.append('antenna_id', String(antennaId))
  form.append('cal_mode', calMode)
  form.append('change_note', notes.changeNote)
  if (notes.lengthCm !== null) form.append('length_cm', String(notes.lengthCm))
  return request('/api/measurements/upload', { method: 'POST', body: form }, fetchFn)
}

export function listMeasurements(
  antennaId: number,
  fetchFn: typeof fetch = fetch,
): Promise<MeasurementRow[]> {
  return request(`/api/measurements?antenna_id=${antennaId}&limit=${HISTORY_LIMIT}`, undefined, fetchFn)
}

export function getMeasurement(id: number, fetchFn: typeof fetch = fetch): Promise<Measurement> {
  return request(`/api/measurements/${id}`, undefined, fetchFn)
}

/** Before/after of two measurements of one antenna. The verdict comes from the server. */
export function compareMeasurements(
  beforeId: number,
  afterId: number,
  fetchFn: typeof fetch = fetch,
): Promise<Comparison> {
  return request(`/api/compare?before=${beforeId}&after=${afterId}`, undefined, fetchFn)
}

export function getHealth(fetchFn: typeof fetch = fetch): Promise<Health> {
  return request('/api/health', undefined, fetchFn)
}

/** Ask the local model to rewrite the card in plain words. It can take a minute or two. */
export function explainMeasurement(id: number, fetchFn: typeof fetch = fetch): Promise<Explanation> {
  return request(`/api/measurements/${id}/explain`, { method: 'POST' }, fetchFn)
}

export function askQuestion(
  id: number,
  question: string,
  fetchFn: typeof fetch = fetch,
): Promise<AskAnswer> {
  return request(`/api/measurements/${id}/ask`, postJson({ question }), fetchFn)
}

export function listCriteria(kind: Kind, fetchFn: typeof fetch = fetch): Promise<Criterion[]> {
  return request(`/api/criteria?kind=${kind}`, undefined, fetchFn)
}

export function listGuides(id: number, fetchFn: typeof fetch = fetch): Promise<GuideTopic[]> {
  return request(`/api/measurements/${id}/guides`, undefined, fetchFn)
}

// Response shapes of the API. Same shape as contract/measurement.json.

export const STAGES = ['none', 'unmatched', 'offtarget', 'narrow', 'good', 'invalid'] as const
export type Stage = (typeof STAGES)[number]

export const SOURCES = ['usb', 'csv', 'stored', 'synthetic'] as const
export type Source = (typeof SOURCES)[number]

export const KINDS = ['monopole', 'patch'] as const
export type Kind = (typeof KINDS)[number]

export const CAL_MODES = ['vna', 'unknown'] as const
export type CalMode = (typeof CAL_MODES)[number]

export interface Antenna {
  id: number
  name: string
  kind: Kind
  target_mhz: number
}

/** One row of `GET /api/antennas/overview`: the antenna plus what is stored for it. */
export interface AntennaOverview extends Antenna {
  measurement_count: number
  last_measured_at: string | null
  last_stage: Stage | null
  last_resonance_mhz: number | null
  /** Source of the latest measurement. Missing on a server older than this field. */
  last_source?: Source | null
}

/** One row of `GET /api/samples`. A hint only; the verdict uses the chosen antenna. */
export interface Sample {
  name: string
  kind: Kind
  target_mhz: number
}

export interface SweepPoint {
  f_mhz: number
  s11_db: number
}

export interface Diagnosis {
  key: string
  title: string
  evidence: string
  action: string
  guide: string
}

/** A narrower range to measure again, with the server's sentence. Only a suggestion. */
export interface Remeasure {
  start_mhz: number
  stop_mhz: number
  note: string
}

export interface Card {
  stage: Stage
  headline: string
  status: string[]
  diagnoses: Diagnosis[]
  /** Missing on cards stored before this field existed. */
  remeasure?: Remeasure | null
}

export interface Measurement {
  id: number
  antenna: Antenna
  source: Source
  cal_mode: CalMode
  measured_at: string
  change_note: string
  /** Conductor length at this measurement, in cm; null when it was not entered. */
  length_cm: number | null
  resonance_mhz: number | null
  s11_db: number | null
  bandwidth_pct: number | null
  sweep: SweepPoint[]
  card: Card
}

/** One row of `GET /api/measurements`: the stored columns without the sweep and the card. */
export interface MeasurementRow {
  id: number
  antenna_id: number
  measured_at: string
  source: Source
  cal_mode: CalMode
  stage: Stage
  resonance_mhz: number | null
  s11_db: number | null
  bandwidth_pct: number | null
  change_note: string
  length_cm: number | null
}

/** `GET /api/compare`. Every number is after minus before; all are null when not comparable. */
export interface Comparison {
  before_id: number
  after_id: number
  target_mhz: number
  /** Coarser sweep spacing around the two resonances; null when a resonance is missing. */
  step_mhz: number | null
  comparable: boolean
  verdict: string
  reasons: string[]
  shift_mhz: number | null
  distance_before_mhz: number | null
  distance_after_mhz: number | null
  distance_change_mhz: number | null
  s11_change_db: number | null
  bandwidth_change_pct: number | null
  stage: { before: Stage; after: Stage }
  change_note: string
  summary: string
}

/** `GET /api/health`. `ollama`: questions are linked by a model. `explain`: show the button. */
export interface Health {
  mode: string
  ollama: boolean
  explain: boolean
  ports: string[]
}

export type ExplainStatus = 'ok' | 'rejected' | 'failed' | 'off'

/** `POST /api/measurements/{id}/explain`. `text` is null unless the status is ok. */
export interface Explanation {
  status: ExplainStatus
  text: string | null
  warnings: string[]
  model: string | null
  seconds: number | null
}

export type AskStatus = 'matched' | 'none' | 'failed'

/** `POST /api/measurements/{id}/ask`. `action` is the card's own value, only when `in_card`. */
export interface AskAnswer {
  status: AskStatus
  key: string | null
  guide: string | null
  in_card: boolean
  action: string | null
}

export interface GuideItem {
  key: string
  guide: string
  in_card: boolean
  action: string | null
}

/** `GET /api/measurements/{id}/guides`: every guide grouped by topic. */
export interface GuideTopic {
  topic: string
  items: GuideItem[]
}

/** One row of `GET /api/criteria`: what a stage means, in the server's sentence. */
export interface Criterion {
  stage: Stage
  text: string
}

export interface AntennaInput {
  name: string
  kind: Kind
  target_mhz: number
}

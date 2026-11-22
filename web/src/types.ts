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

export interface Card {
  stage: Stage
  headline: string
  status: string[]
  diagnoses: Diagnosis[]
}

export interface Measurement {
  id: number
  antenna: Antenna
  source: Source
  cal_mode: CalMode
  measured_at: string
  change_note: string
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
}

export interface AntennaInput {
  name: string
  kind: Kind
  target_mhz: number
}

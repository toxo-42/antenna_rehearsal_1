// The sidebar summary of one antenna, from its measurement list (newest first). Pure functions.

import { isTruncated } from './trend.ts'
import type { MeasurementRow, Stage } from './types.ts'

export interface AntennaSummary {
  count: number
  latestStage: Stage | null
  latestResonanceMhz: number | null
}

/** Count plus the newest row's stage and resonance. Nothing is taken from older rows. */
export function antennaSummary(rows: MeasurementRow[]): AntennaSummary {
  const newest = rows[0]
  return {
    count: rows.length,
    latestStage: newest?.stage ?? null,
    latestResonanceMhz: newest?.resonance_mhz ?? null,
  }
}

/** "6회"; a full page reads "200회 이상" because older measurements may be missing. */
export function countText(count: number): string {
  return isTruncated(count) ? `${count}회 이상` : `${count}회`
}

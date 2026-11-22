// Resonance frequency by measurement order, with the target line. Pure functions.

import { HISTORY_LIMIT } from './api.ts'
import type { PlotBox } from './chart.ts'
import type { MeasurementRow, Source } from './types.ts'

const MARGIN_RATIO = 0.1
const MIN_SPAN_MHZ = 1

export interface TrendPoint {
  id: number
  order: number
  x: number
  y: number
  resonanceMhz: number
  source: Source
}

export interface TrendModel {
  points: TrendPoint[]
  /** True when any point is synthetic: the chart must then say "합성 데이터". */
  hasSynthetic: boolean
  count: number
  fMin: number
  fMax: number
  targetY: number
}

/** A full page means older measurements may be missing from what the screen holds. */
export function isTruncated(rowCount: number): boolean {
  return rowCount >= HISTORY_LIMIT
}

/** "3번째", or "최근 200건 중 3번째" when older measurements are not loaded. */
export function orderText(order: number, truncated: boolean): string {
  return truncated ? `최근 ${HISTORY_LIMIT}건 중 ${order}번째` : `${order}번째`
}

/** Oldest first; measurements taken in the same second keep their id order. */
export function inMeasurementOrder(rows: readonly MeasurementRow[]): MeasurementRow[] {
  return [...rows].sort((a, b) => a.measured_at.localeCompare(b.measured_at) || a.id - b.id)
}

function frequencyRange(values: number[]): [number, number] {
  let low = Math.min(...values)
  let high = Math.max(...values)
  const span = Math.max(high - low, MIN_SPAN_MHZ)
  low -= span * MARGIN_RATIO
  high += span * MARGIN_RATIO
  return [low, high]
}

/** Order 1 is the first measurement. A measurement without resonance keeps its order but no point. */
export function trendModel(rows: readonly MeasurementRow[], targetMhz: number, box: PlotBox): TrendModel {
  const ordered = inMeasurementOrder(rows)
  const resonances = ordered.flatMap((row) => (row.resonance_mhz === null ? [] : [row.resonance_mhz]))
  const [fMin, fMax] = frequencyRange([targetMhz, ...resonances])
  const xOf = (index: number) =>
    ordered.length > 1 ? box.left + (index / (ordered.length - 1)) * box.width : box.left + box.width / 2
  const yOf = (f: number) => box.top + ((fMax - f) / (fMax - fMin)) * box.height
  const points = ordered.flatMap((row, index) =>
    row.resonance_mhz === null
      ? []
      : [
          {
            id: row.id,
            order: index + 1,
            x: xOf(index),
            y: yOf(row.resonance_mhz),
            resonanceMhz: row.resonance_mhz,
            source: row.source,
          },
        ],
  )
  const hasSynthetic = points.some((point) => point.source === 'synthetic')
  return { points, hasSynthetic, count: ordered.length, fMin, fMax, targetY: yOf(targetMhz) }
}
